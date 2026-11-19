'''SAM.gov public monthly extracts on disk: month parsing, acquisition, import and month
selection.'''

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import version

import pytest
from vendor_link_fixtures import (  # noqa: F401
    EXTRACT_NAME,
    FAKE_KEY,
    MONTH,
    FakeSam,
    extract_answer,
    extract_name,
    install_sam,
    no_live_sam,
    redirect_answer,
    sample_extract,
    zip_bytes,
)

from embedding_data import manifest, paths, sam_access, sam_raw, usaspending_raw

EXTRACTS = 'raw/sam/entity-extract/public-monthly-v2'
NOT_A_ZIP = b'PK\x03\x04garbage that is not an archive'
FAILED = 'SAM.gov extract request failed; details suppressed'


def month_directory(data_directory, month=MONTH):
    return sam_raw.month_dir(data_directory, month)


def manifest_lines(data_directory):
    path = paths.manifest_path(data_directory)
    return path.read_text().splitlines() if path.exists() else []


def assert_nothing_written(data_directory):
    '''No final file, no `.part` and no manifest line anywhere under the data root.'''
    leftovers = [file for file in data_directory.rglob('*') if not file.is_dir()]
    assert leftovers == []
    assert manifest_lines(data_directory) == []


# --- names, months and layout


def test_constants_and_layout(data_directory):
    assert sam_raw.SOURCE == 'sam'
    assert sam_raw.NAME.pattern == r'SAM_PUBLIC_UTF-8_MONTHLY_V2_(\d{4})(\d{2})\d{2}\.ZIP'
    assert sam_raw.month_dir(data_directory, '2026-11') == data_directory / EXTRACTS / '2026-11'


@pytest.mark.parametrize('month', ['2026-01', '2026-09', '2026-10', '2026-12', '1999-07'])
def test_parse_month_accepts_yyyy_mm(month):
    assert sam_raw.parse_month(month) == month


@pytest.mark.parametrize('month', [
    '2026-1', '2026-111', '2026-00', '2026-13', '2026-20', '2026/11', '11/2026', '202611',
    '26-11', '2026-11-01', '../x', ' 2026-11', '2026-11 ', '2026-11\n', '',
    '٢٠٢٦-11', '2026-١١'])
def test_parse_month_refuses_anything_else(month):
    with pytest.raises(ValueError, match='YYYY-MM'):
        sam_raw.parse_month(month)


@pytest.mark.parametrize('first', ['sam_access', 'sam_raw'])
def test_the_two_sam_modules_import_in_either_order(first, tmp_path):
    result = subprocess.run(
        [sys.executable, '-c',
         f'import embedding_data.{first}; from embedding_data import sam_access, sam_raw; '
         "print(sam_access.extract_url('2026-11').endswith('date=11/2026&charset=UTF8'), "
         "bool(sam_raw.NAME.fullmatch('SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.ZIP')))"],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'True True'


# --- acquire


def test_acquire_records_the_key_free_url(data_directory, monkeypatch):
    install_sam(monkeypatch, FakeSam(extract_answer()))
    path = sam_raw.acquire(data_directory, '2026-11', credential=FAKE_KEY)
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert entry.source_url == sam_access.extract_url('2026-11')
    assert 'api_key' not in entry.source_url and entry.through_date is None


def test_acquire_publishes_the_delivered_bytes_under_the_delivered_name(data_directory,
                                                                        monkeypatch):
    server = install_sam(monkeypatch, FakeSam(redirect_answer(), extract_answer()))
    before = datetime.now(UTC).replace(microsecond=0)
    path = sam_raw.acquire(data_directory, MONTH, credential=FAKE_KEY)
    assert path == month_directory(data_directory) / EXTRACT_NAME
    assert path.read_bytes() == sample_extract()
    assert sorted(file.name for file in path.parent.iterdir()) == [EXTRACT_NAME]
    (line,) = manifest_lines(data_directory)
    recorded = json.loads(line)
    assert recorded['path'] == f'sam/entity-extract/public-monthly-v2/2026-11/{EXTRACT_NAME}'
    assert recorded['sha256'] == hashlib.sha256(sample_extract()).hexdigest()
    assert recorded['size'] == len(sample_extract())
    assert (recorded['client'], recorded['client_version'], recorded['source_url'],
            recorded['proxies'], recorded['through_date']) == (
        'httpx', version('httpx'), sam_access.extract_url(MONTH), [], None)
    assert before <= datetime.fromisoformat(recorded['retrieved_at']) <= datetime.now(UTC)
    assert server.requests[0].url.params['api_key'] == FAKE_KEY


@pytest.mark.parametrize('month', ['2027-01', '2026-12'])
def test_acquire_requests_and_files_the_month_it_is_given(month, data_directory, monkeypatch):
    server = install_sam(monkeypatch, FakeSam(
        extract_answer(sample_extract(month), name=extract_name(month))))
    path = sam_raw.acquire(data_directory, month, credential=FAKE_KEY)
    assert server.requests[0].url.params['date'] == f'{month[5:]}/{month[:4]}'
    assert path == month_directory(data_directory, month) / extract_name(month)


def test_acquire_sends_the_credential_it_is_given(data_directory, monkeypatch):
    server = install_sam(monkeypatch, FakeSam(extract_answer()))
    sam_raw.acquire(data_directory, MONTH, credential='OTHERfake0123456789key')
    assert server.requests[0].url.params['api_key'] == 'OTHERfake0123456789key'


def test_acquire_accepts_an_existing_empty_month_directory(data_directory, monkeypatch):
    install_sam(monkeypatch, FakeSam(extract_answer()))
    month_directory(data_directory).mkdir(parents=True)
    assert sam_raw.acquire(data_directory, MONTH, credential=FAKE_KEY).is_file()


def occupy_with_file(data_directory):
    directory = month_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / extract_name(MONTH, '09')).write_bytes(sample_extract())


def occupy_with_part(data_directory):
    directory = month_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / 'download.part').write_bytes(b'interrupted')


def occupy_with_directory(data_directory):
    (month_directory(data_directory) / 'nested').mkdir(parents=True)


def occupy_with_a_file_in_place_of_the_directory(data_directory):
    directory = month_directory(data_directory)
    directory.parent.mkdir(parents=True)
    directory.write_bytes(sample_extract())


def occupy_with_a_symlinked_directory(data_directory):
    target = data_directory.parent / 'elsewhere'
    target.mkdir()
    directory = month_directory(data_directory)
    directory.parent.mkdir(parents=True)
    directory.symlink_to(target, target_is_directory=True)


def occupy_with_a_symlinked_source_directory(data_directory):
    target = data_directory.parent / 'elsewhere'
    target.mkdir()
    (data_directory / 'raw').mkdir(parents=True)
    (data_directory / 'raw' / 'sam').symlink_to(target, target_is_directory=True)


def occupy_with_a_symlinked_raw_directory(data_directory):
    target = data_directory.parent / 'elsewhere'
    target.mkdir()
    data_directory.mkdir()
    (data_directory / 'raw').symlink_to(target, target_is_directory=True)


OCCUPATIONS = {
    occupy_with_file: 'occupied',
    occupy_with_part: 'occupied',
    occupy_with_directory: 'occupied',
    occupy_with_a_file_in_place_of_the_directory: 'occupied',
    occupy_with_a_symlinked_directory: 'symlink',
    occupy_with_a_symlinked_source_directory: 'symlink',
    occupy_with_a_symlinked_raw_directory: 'symlink',
}


@pytest.mark.parametrize('occupy', OCCUPATIONS, ids=lambda function: function.__name__)
def test_acquire_refuses_an_occupied_month_before_any_request(occupy, data_directory,
                                                              monkeypatch):
    server = install_sam(monkeypatch, FakeSam(extract_answer()))
    occupy(data_directory)
    with pytest.raises(ValueError, match=OCCUPATIONS[occupy]):
        sam_raw.acquire(data_directory, MONTH, credential=FAKE_KEY)
    assert server.requests == []
    assert manifest_lines(data_directory) == []


@pytest.mark.parametrize('month', ['2026-13', '2026-1', '../x'])
def test_acquire_refuses_a_bad_month_before_any_request(month, data_directory, monkeypatch):
    server = install_sam(monkeypatch, FakeSam(extract_answer()))
    with pytest.raises(ValueError, match='YYYY-MM'):
        sam_raw.acquire(data_directory, month, credential=FAKE_KEY)
    assert server.requests == []
    assert not data_directory.exists()


@pytest.mark.parametrize('delivered', ['2026-10', '2025-11', '2026-12'])
def test_acquire_refuses_a_delivered_name_of_another_month(delivered, data_directory,
                                                           monkeypatch):
    server = install_sam(monkeypatch, FakeSam(extract_answer(name=extract_name(delivered))))
    with pytest.raises(ValueError, match='month'):
        sam_raw.acquire(data_directory, MONTH, credential=FAKE_KEY)
    assert len(server.requests) == 1
    assert list(month_directory(data_directory).iterdir()) == []
    assert manifest_lines(data_directory) == []


def test_acquire_refused_answer_leaves_an_empty_month_directory(data_directory, monkeypatch):
    install_sam(monkeypatch, FakeSam(extract_answer(NOT_A_ZIP)))
    with pytest.raises(ValueError, match=FAILED):
        sam_raw.acquire(data_directory, MONTH, credential=FAKE_KEY)
    assert list(month_directory(data_directory).iterdir()) == []
    assert manifest_lines(data_directory) == []


def test_acquire_never_removes_a_part_it_did_not_create(data_directory, monkeypatch):
    # The occupancy check normally stops this first, so switch it off to reach the open.
    install_sam(monkeypatch, FakeSam(extract_answer()))
    monkeypatch.setattr(usaspending_raw, 'require_free_directory', lambda *arguments: None)
    directory = month_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / 'download.part').write_bytes(b'someone else')
    with pytest.raises(ValueError, match=FAILED):
        sam_raw.acquire(data_directory, MONTH, credential=FAKE_KEY)
    assert sorted(file.name for file in directory.iterdir()) == ['download.part']
    assert (directory / 'download.part').read_bytes() == b'someone else'
    assert manifest_lines(data_directory) == []


def record_without_a_file(data_directory, tmp_path, name=EXTRACT_NAME, month=MONTH):
    '''Put a final path of `month` in the manifest while no file exists there.'''
    scratch = make_original(tmp_path, 'scratch.zip', folder='scratch')
    earlier = manifest.describe_file(
        scratch, scratch.parent, retrieved_at=datetime.now(UTC), client='httpx',
        client_version='1')
    manifest.append_entries(paths.manifest_path(data_directory), [replace(
        earlier, path=f'sam/entity-extract/public-monthly-v2/{month}/{name}')])
    return manifest_lines(data_directory)


def test_acquire_removes_its_part_when_publishing_fails(data_directory, tmp_path, monkeypatch):
    install_sam(monkeypatch, FakeSam(extract_answer()))
    before = record_without_a_file(data_directory, tmp_path)
    with pytest.raises(ValueError, match='already recorded'):
        sam_raw.acquire(data_directory, MONTH, credential=FAKE_KEY)
    assert list(month_directory(data_directory).iterdir()) == []
    assert manifest_lines(data_directory) == before


# --- import


def make_original(tmp_path, name=EXTRACT_NAME, content=None, folder='downloads'):
    original = tmp_path / folder / name
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(sample_extract() if content is None else content)
    return original


def test_import_records_a_proxy_retrieval_time(data_directory, tmp_path):
    original = make_original(tmp_path)
    path = sam_raw.import_file(data_directory, original, month=MONTH)
    assert path == month_directory(data_directory) / EXTRACT_NAME
    assert path.read_bytes() == original.read_bytes()
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert (entry.client, entry.source_url, entry.proxies, entry.through_date) == (
        'manual-import', None, ('retrieved_at',), None)
    assert entry.client_version == version('embedding-data')
    assert entry.sha256 == hashlib.sha256(original.read_bytes()).hexdigest()
    assert original.exists()
    assert sorted(file.name for file in path.parent.iterdir()) == [EXTRACT_NAME]


def test_import_requires_the_utf8_name_and_month(data_directory, tmp_path):
    ascii_name = make_original(tmp_path, 'SAM_PUBLIC_MONTHLY_V2_20261102.ZIP', folder='ascii')
    october = make_original(tmp_path, extract_name('2026-10'), folder='october')
    for original in (ascii_name, october):
        with pytest.raises(ValueError):
            sam_raw.import_file(data_directory, original, month='2026-11')
    assert_nothing_written(data_directory)


def prepare_symlink(tmp_path):
    target = make_original(tmp_path, 'real.zip')
    link = tmp_path / 'downloads' / EXTRACT_NAME
    link.symlink_to(target)
    return link


def prepare_directory(tmp_path):
    folder = tmp_path / 'downloads' / EXTRACT_NAME
    folder.mkdir(parents=True)
    return folder


IMPORT_REFUSALS = {
    'symlink': (MONTH, prepare_symlink, 'not a regular file'),
    'directory': (MONTH, prepare_directory, 'not a regular file'),
    'missing': (MONTH, lambda tmp_path: tmp_path / 'downloads' / EXTRACT_NAME,
                'not a regular file'),
    'empty': (MONTH, lambda tmp_path: make_original(tmp_path, content=b''), 'empty'),
    'not_a_zip': (MONTH, lambda tmp_path: make_original(tmp_path, content=NOT_A_ZIP),
                  'not a ZIP file'),
    'prefixed_zip': (MONTH, lambda tmp_path: make_original(
        tmp_path, content=b'XXXX' + sample_extract()), 'not a ZIP file'),
    'ascii_name': (MONTH, lambda tmp_path: make_original(
        tmp_path, 'SAM_PUBLIC_MONTHLY_V2_20261102.ZIP'), 'month'),
    'lowercase_name': (MONTH, lambda tmp_path: make_original(tmp_path, EXTRACT_NAME.lower()),
                       'month'),
    'lowercase_suffix': (MONTH, lambda tmp_path: make_original(
        tmp_path, EXTRACT_NAME.removesuffix('.ZIP') + '.zip'), 'month'),
    'name_with_a_prefix': (MONTH, lambda tmp_path: make_original(tmp_path, 'x' + EXTRACT_NAME),
                           'month'),
    'name_with_a_suffix': (MONTH, lambda tmp_path: make_original(tmp_path, EXTRACT_NAME + '.x'),
                           'month'),
    'name_of_another_month': (MONTH, lambda tmp_path: make_original(
        tmp_path, extract_name('2026-10')), 'month'),
    'name_of_another_year': (MONTH, lambda tmp_path: make_original(
        tmp_path, extract_name('2025-11')), 'month'),
    'bad_month': ('2026-13', lambda tmp_path: make_original(
        tmp_path, 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261302.ZIP'), 'YYYY-MM'),
}


@pytest.mark.parametrize('case', IMPORT_REFUSALS)
def test_import_refuses_symlinks_bad_files_bad_names_and_other_months(case, data_directory,
                                                                     tmp_path):
    month, prepare, message = IMPORT_REFUSALS[case]
    original = prepare(tmp_path)
    with pytest.raises(ValueError, match=message):
        sam_raw.import_file(data_directory, original, month=month)
    assert_nothing_written(data_directory)


@pytest.mark.parametrize('occupy', OCCUPATIONS, ids=lambda function: function.__name__)
def test_import_refuses_an_occupied_month_directory(occupy, data_directory, tmp_path):
    original = make_original(tmp_path)
    occupy(data_directory)
    with pytest.raises(ValueError, match=OCCUPATIONS[occupy]):
        sam_raw.import_file(data_directory, original, month=MONTH)
    assert manifest_lines(data_directory) == []


def test_import_never_replaces_an_earlier_import(data_directory, tmp_path):
    first = make_original(tmp_path)
    path = sam_raw.import_file(data_directory, first, month=MONTH)
    second = make_original(tmp_path, extract_name(MONTH, '09'),
                           zip_bytes({'other.dat': b'x'}), 'second')
    before = manifest_lines(data_directory)
    with pytest.raises(ValueError, match='occupied'):
        sam_raw.import_file(data_directory, second, month=MONTH)
    assert path.read_bytes() == first.read_bytes()
    assert manifest_lines(data_directory) == before
    assert sorted(file.name for file in path.parent.iterdir()) == [EXTRACT_NAME]


def test_import_never_writes_over_or_removes_a_part_it_did_not_create(data_directory, tmp_path,
                                                                      monkeypatch):
    original = make_original(tmp_path)
    monkeypatch.setattr(usaspending_raw, 'require_free_directory', lambda *arguments: None)
    directory = month_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / f'{EXTRACT_NAME}.part').write_bytes(b'someone else')
    with pytest.raises(FileExistsError):
        sam_raw.import_file(data_directory, original, month=MONTH)
    assert not (directory / EXTRACT_NAME).exists()
    assert manifest_lines(data_directory) == []
    assert (directory / f'{EXTRACT_NAME}.part').read_bytes() == b'someone else'


def test_import_removes_its_part_when_publishing_fails(data_directory, tmp_path):
    original = make_original(tmp_path)
    before = record_without_a_file(data_directory, tmp_path)
    with pytest.raises(ValueError, match='already recorded'):
        sam_raw.import_file(data_directory, original, month=MONTH)
    assert list(month_directory(data_directory).iterdir()) == []
    assert manifest_lines(data_directory) == before


def test_import_refuses_a_copy_whose_hash_differs_and_leaves_nothing(data_directory, tmp_path,
                                                                     monkeypatch):
    original = make_original(tmp_path)

    def corrupt(source, target):
        target.write(b'corrupt copy')

    monkeypatch.setattr(sam_raw.shutil, 'copyfileobj', corrupt)
    with pytest.raises(ValueError, match='SHA-256 changed while copying'):
        sam_raw.import_file(data_directory, original, month=MONTH)
    assert_nothing_written(data_directory)


# --- month selection


def import_month(data_directory, tmp_path, month):
    original = make_original(tmp_path, extract_name(month), sample_extract(month), month)
    return sam_raw.import_file(data_directory, original, month=month)


def test_month_selection_ignores_other_months(data_directory, tmp_path):
    first = import_month(data_directory, tmp_path, '2026-11')
    second = import_month(data_directory, tmp_path, '2026-12')
    assert sam_raw.select_extract(data_directory, '2026-11') == first
    assert sam_raw.select_extract(data_directory, '2026-12') == second
    assert first.read_bytes() != second.read_bytes()


def add_a_file(file):
    (file.parent / extract_name(MONTH, '09')).write_bytes(sample_extract())


def add_a_part(file):
    (file.parent / 'download.part').write_bytes(b'interrupted')


def add_a_directory(file):
    (file.parent / 'nested').mkdir()


def remove_the_file(file):
    file.unlink()


def remove_the_month(file):
    shutil.rmtree(file.parent)


def replace_with_a_symlink(file):
    copy = file.parent.parent / 'copy.zip'
    shutil.copy(file, copy)
    file.unlink()
    file.symlink_to(copy)


def replace_the_month_directory_with_a_symlink(file):
    moved = file.parent.parent / 'moved'
    file.parent.rename(moved)
    file.parent.symlink_to(moved, target_is_directory=True)


def change_the_bytes(file):
    original = file.read_bytes()
    file.write_bytes(bytes([original[0] ^ 1]) + original[1:])


def rename_and_record(new_name):
    '''Move the file to `new_name` and record it there, so only its name is wrong.'''
    def damage(file):
        data_directory = file.parents[5]
        renamed = file.rename(file.with_name(new_name))
        entry = manifest.describe_file(
            renamed, renamed.parent, retrieved_at=datetime.now(UTC), client='manual-import',
            client_version='1')
        manifest.append_entries(paths.manifest_path(data_directory), [replace(
            entry, path=renamed.relative_to(data_directory / 'raw').as_posix())])
    return damage


SELECTION_FAILURES = {
    'extra_file': (add_a_file, 'missing or extra raw file'),
    'extra_part': (add_a_part, 'missing or extra raw file'),
    'extra_directory': (add_a_directory, 'missing or extra raw file'),
    'empty_month': (remove_the_file, 'missing or extra raw file'),
    'missing_month': (remove_the_month, 'missing or extra raw file'),
    'symlinked_file': (replace_with_a_symlink, 'missing or extra raw file'),
    'symlinked_month_directory': (replace_the_month_directory_with_a_symlink, 'symlink'),
    'recorded_name_of_another_month': (rename_and_record(extract_name('2026-10')),
                                       'missing or extra raw file'),
    'recorded_lowercase_name': (rename_and_record(EXTRACT_NAME.lower()),
                                'missing or extra raw file'),
    'recorded_zip_name': (rename_and_record('extract.zip'), 'missing or extra raw file'),
    'changed_bytes': (change_the_bytes, 'raw file changed'),
}


@pytest.mark.parametrize('case', SELECTION_FAILURES)
def test_month_selection_refuses_any_other_state(case, data_directory, tmp_path):
    file = import_month(data_directory, tmp_path, MONTH)
    damage, message = SELECTION_FAILURES[case]
    damage(file)
    with pytest.raises(ValueError, match=message):
        sam_raw.select_extract(data_directory, MONTH)


def test_month_selection_refuses_a_file_the_manifest_does_not_record(data_directory):
    directory = month_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / EXTRACT_NAME).write_bytes(sample_extract())
    with pytest.raises(ValueError, match='raw file is not recorded'):
        sam_raw.select_extract(data_directory, MONTH)


@pytest.mark.parametrize('month', ['2026-13', '../x', '2026-1'])
def test_month_selection_refuses_a_bad_month(month, data_directory):
    with pytest.raises(ValueError, match='YYYY-MM'):
        sam_raw.select_extract(data_directory, month)
