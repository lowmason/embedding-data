import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from embedding_data import manifest, paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ABC_SHA256 = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
RETRIEVED_AT = datetime(2026, 10, 12, 16, 50, 59, tzinfo=UTC)


@pytest.fixture
def raw_file(data_directory):
    file = paths.raw_dir(data_directory, 'acs') / 'core/usa_00001/usa_00001.xml'
    file.parent.mkdir(parents=True)
    file.write_bytes(b'abc')
    return file


def describe(file, data_directory, *, retrieved_at=RETRIEVED_AT, **provenance):
    return manifest.describe_file(
        file,
        paths.manifest_path(data_directory).parent,
        retrieved_at=retrieved_at,
        client='ipumspy',
        client_version='0.8.2',
        **provenance,
    )


def test_layout_keeps_raw_derived_and_preview_under_one_root(tmp_path):
    assert paths.DATA_DIR == PROJECT_ROOT / 'data'
    assert paths.raw_dir(tmp_path, 'acs') == tmp_path / 'raw/acs'
    assert paths.derived_dir(tmp_path, 'acs') == tmp_path / 'derived/acs'
    assert paths.preview_dir(tmp_path, 'acs') == tmp_path / 'preview/acs'
    assert paths.manifest_path(tmp_path) == tmp_path / 'raw/manifest.jsonl'


def test_sha256_file_streams_a_known_digest(raw_file):
    assert manifest.sha256_file(raw_file) == ABC_SHA256


def test_describe_file_records_path_hash_and_provenance_in_utc(raw_file, data_directory):
    eastern = timezone(timedelta(hours=-4))

    entry = describe(
        raw_file,
        data_directory,
        retrieved_at=datetime(2026, 10, 12, 12, 50, 59, tzinfo=eastern),
        collection='usa',
        extract_number=1,
        samples=['us2023a', 'us2024a'],
    )

    assert entry == manifest.ManifestEntry(
        path='acs/core/usa_00001/usa_00001.xml',
        sha256=ABC_SHA256,
        size=3,
        retrieved_at='2026-10-12T16:50:59+00:00',
        client='ipumspy',
        client_version='0.8.2',
        collection='usa',
        extract_number=1,
        samples=('us2023a', 'us2024a'),
    )


def test_describe_file_rejects_a_naive_retrieval_time(raw_file, data_directory):
    with pytest.raises(ValueError, match='timezone-aware'):
        describe(raw_file, data_directory, retrieved_at=datetime(2026, 10, 12, 16, 50, 59))


def test_read_manifest_is_empty_before_the_first_download(data_directory):
    assert manifest.read_manifest(paths.manifest_path(data_directory)) == []


def test_appending_nothing_leaves_no_manifest(data_directory):
    manifest_path = paths.manifest_path(data_directory)

    manifest.append_entries(manifest_path, [])

    assert not manifest_path.exists()


def test_entries_round_trip_as_one_json_line_each_in_recording_order(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    pdf = paths.raw_dir(data_directory, 'osha') / 'dictionary.pdf'
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b'%PDF')
    first = describe(raw_file, data_directory, collection='usa', extract_number=1)
    second = describe(
        pdf, data_directory, source_url='https://www.osha.gov/dictionary.pdf',
        proxies=['retrieved_at'],
    )

    manifest.append_entries(manifest_path, [first])
    manifest.append_entries(manifest_path, [second])

    assert manifest.read_manifest(manifest_path) == [first, second]
    lines = manifest_path.read_text().splitlines()
    assert [json.loads(line)['path'] for line in lines] == [first.path, 'osha/dictionary.pdf']


def test_a_recorded_path_is_never_recorded_again(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    manifest.append_entries(manifest_path, [describe(raw_file, data_directory)])
    recorded = manifest_path.read_bytes()
    raw_file.write_bytes(b'replaced')

    with pytest.raises(ValueError, match='usa_00001.xml is already recorded'):
        manifest.append_entries(manifest_path, [describe(raw_file, data_directory)])

    assert manifest_path.read_bytes() == recorded


def test_a_duplicate_within_one_append_writes_nothing(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory)

    with pytest.raises(ValueError, match='usa_00001.xml is repeated in this append'):
        manifest.append_entries(manifest_path, [entry, entry])

    assert not manifest_path.exists()


def test_entry_for_finds_a_raw_file_by_location(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory)
    manifest.append_entries(manifest_path, [entry])

    assert manifest.entry_for(manifest_path, raw_file) == entry
    with pytest.raises(KeyError, match='usa_00002.xml'):
        manifest.entry_for(manifest_path, raw_file.with_name('usa_00002.xml'))


def test_through_date_is_recorded_as_an_iso_date(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory, through_date=date(2026, 8, 31))

    manifest.append_entries(manifest_path, [entry])

    assert json.loads(manifest_path.read_text())['through_date'] == '2026-08-31'
    assert manifest.read_manifest(manifest_path) == [entry]


def test_a_line_recorded_before_through_date_existed_still_reads(data_directory):
    manifest_path = paths.manifest_path(data_directory)
    manifest_path.parent.mkdir(parents=True)
    stage_1_line = {
        'path': 'osha/case_detail_data_dictionary_2026.pdf', 'sha256': ABC_SHA256,
        'size': 3, 'retrieved_at': '2026-10-12T15:28:00+00:00', 'client': 'httpx',
        'client_version': '0.28.1', 'source_url': 'https://www.osha.gov/x.pdf',
        'collection': None, 'extract_number': None, 'samples': [], 'proxies': [],
    }
    manifest_path.write_text(json.dumps(stage_1_line) + '\n')

    [entry] = manifest.read_manifest(manifest_path)

    assert entry.path == 'osha/case_detail_data_dictionary_2026.pdf'
    assert entry.through_date is None


def test_entry_for_verifies_present_bytes(raw_file, data_directory):
    file = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory)
    manifest.append_entries(file, [entry])
    raw_file.write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA-256 .*differs'):
        manifest.entry_for(file, raw_file)
    raw_file.unlink()
    assert manifest.recorded_entry_for(file, raw_file) == entry
    with pytest.raises(FileNotFoundError):
        manifest.entry_for(file, raw_file)
