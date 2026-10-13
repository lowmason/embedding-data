import gzip
import json
import os
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from embedding_data import manifest, paths, raw_backfill
from embedding_data import osha_benchmark_download as osha

LOCK = """version = 1

[[package]]
name = "httpx"
version = "0.28.1"

[[package]]
name = "ipumspy"
version = "0.8.2"
"""
DEFINED = datetime(2026, 10, 12, 16, 41, 39, tzinfo=UTC).timestamp()
DELIVERED = datetime(2026, 10, 12, 16, 50, 59, tzinfo=UTC).timestamp()
PROXIES = ('retrieved_at', 'client_version')
OSHA_CSV = osha.file_name(osha.CSV_URL)
OSHA_PDF = osha.file_name(osha.DICTIONARY_URL)
OSHA_PARQUET = OSHA_CSV.replace('.csv', '.parquet')


def write_legacy_extract(data_dir, source, set_name, name, samples):
    '''One extract as the pre-manifest commands left it: four files side by side.'''
    set_dir = paths.raw_dir(data_dir, source) / set_name
    set_dir.mkdir(parents=True)
    definition = set_dir / 'extract.json'
    definition.write_text(json.dumps({
        'description': f'{source.upper()} embedding benchmark: {set_name}',
        'collection': name.split('_')[0],
        'samples': {sample: {} for sample in samples},
    }))
    (set_dir / f'{name}.csv.gz').write_bytes(gzip.compress(f'{name}\n1\n'.encode()))
    (set_dir / f'{name}.xml').write_text(f'<codeBook>{name}</codeBook>\n')
    (set_dir / f'{name}.parquet').write_bytes(f'PAR1 {name}'.encode())
    os.utime(definition, (DEFINED, DEFINED))
    for suffix in ('.csv.gz', '.xml'):
        os.utime(set_dir / f'{name}{suffix}', (DELIVERED, DELIVERED))


@pytest.fixture
def legacy(data_directory, tmp_path):
    '''A pre-Stage-1 data tree and a uv.lock; returns (data_dir, lock_path).'''
    write_legacy_extract(data_directory, 'acs', 'core', 'usa_00001', ['us2023a', 'us2024a'])
    write_legacy_extract(data_directory, 'cps', 'monthly', 'cps_00001', ['cps2025_01b'])
    osha_dir = paths.raw_dir(data_directory, 'osha')
    osha_dir.mkdir(parents=True)
    (osha_dir / OSHA_CSV).write_bytes(b'ID\r\n1\r\n')
    (osha_dir / OSHA_PDF).write_bytes(b'%PDF-1.6 fixture')
    (osha_dir / OSHA_PARQUET).write_bytes(b'PAR1 osha')
    for name in (OSHA_CSV, OSHA_PDF):
        os.utime(osha_dir / name, (DELIVERED, DELIVERED))
    lock_path = tmp_path / 'uv.lock'
    lock_path.write_text(LOCK)
    return data_directory, lock_path


def tree(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def test_raw_files_move_into_extract_directories_and_parquet_leaves_raw(legacy):
    data_dir, lock_path = legacy
    before = tree(data_dir)

    raw_backfill.backfill(data_dir, lock_path)

    after = tree(data_dir)
    moved = {
        'raw/acs/core/extract.json': 'raw/acs/core/usa_00001/extract.json',
        'raw/acs/core/usa_00001.csv.gz': 'raw/acs/core/usa_00001/usa_00001.csv.gz',
        'raw/acs/core/usa_00001.xml': 'raw/acs/core/usa_00001/usa_00001.xml',
        'raw/acs/core/usa_00001.parquet': 'derived/acs/core/usa_00001.parquet',
        'raw/cps/monthly/extract.json': 'raw/cps/monthly/cps_00001/extract.json',
        'raw/cps/monthly/cps_00001.csv.gz': 'raw/cps/monthly/cps_00001/cps_00001.csv.gz',
        'raw/cps/monthly/cps_00001.xml': 'raw/cps/monthly/cps_00001/cps_00001.xml',
        'raw/cps/monthly/cps_00001.parquet': 'derived/cps/monthly/cps_00001.parquet',
        f'raw/osha/{OSHA_PARQUET}': f'derived/osha/{OSHA_PARQUET}',
    }
    expected = {moved.get(path, path): contents for path, contents in before.items()}
    expected['raw/manifest.jsonl'] = after['raw/manifest.jsonl']
    assert after == expected


def test_every_raw_file_is_recorded_with_its_proxies_flagged(legacy):
    data_dir, lock_path = legacy

    appended = raw_backfill.backfill(data_dir, lock_path)

    assert manifest.read_manifest(paths.manifest_path(data_dir)) == appended
    raw = data_dir / 'raw'
    assert [entry.path for entry in appended] == [
        'acs/core/usa_00001/extract.json',
        'acs/core/usa_00001/usa_00001.csv.gz',
        'acs/core/usa_00001/usa_00001.xml',
        'cps/monthly/cps_00001/extract.json',
        'cps/monthly/cps_00001/cps_00001.csv.gz',
        'cps/monthly/cps_00001/cps_00001.xml',
        f'osha/{OSHA_PDF}',
        f'osha/{OSHA_CSV}',
    ]
    for entry in appended:
        assert entry.sha256 == manifest.sha256_file(raw / entry.path)
        assert entry.proxies == PROXIES
    data = appended[1]
    assert data == manifest.ManifestEntry(
        path='acs/core/usa_00001/usa_00001.csv.gz',
        sha256=data.sha256,
        size=(raw / data.path).stat().st_size,
        retrieved_at='2026-10-12T16:50:59+00:00',
        client='ipumspy',
        client_version='0.8.2',
        collection='usa',
        extract_number=1,
        samples=('us2023a', 'us2024a'),
        proxies=PROXIES,
    )
    assert appended[0].retrieved_at == '2026-10-12T16:41:39+00:00'
    assert appended[3].samples == ('cps2025_01b',)
    assert appended[-1] == manifest.ManifestEntry(
        path=f'osha/{OSHA_CSV}',
        sha256=appended[-1].sha256,
        size=len(b'ID\r\n1\r\n'),
        retrieved_at='2026-10-12T16:50:59+00:00',
        client='httpx',
        client_version='0.28.1',
        source_url=osha.CSV_URL,
        proxies=PROXIES,
    )


def test_a_migrated_tree_is_left_as_it_is(legacy):
    data_dir, lock_path = legacy
    raw_backfill.backfill(data_dir, lock_path)
    before = tree(data_dir)

    assert raw_backfill.backfill(data_dir, lock_path) == []
    assert tree(data_dir) == before


def make_definition_newer(data_dir):
    later = DELIVERED + 60
    os.utime(data_dir / 'raw/cps/monthly/extract.json', (later, later))


def point_definition_at_another_set(data_dir):
    definition = data_dir / 'raw/cps/monthly/extract.json'
    definition.write_text(json.dumps({
        'description': 'CPS embedding benchmark: asec', 'collection': 'cps', 'samples': {},
    }))
    os.utime(definition, (DEFINED, DEFINED))


def remove_codebook(data_dir):
    (data_dir / 'raw/cps/monthly/cps_00001.xml').unlink()


def add_second_extract(data_dir):
    (data_dir / 'raw/cps/monthly/cps_00002.csv.gz').write_bytes(gzip.compress(b'x'))


@pytest.mark.parametrize(
    ('corrupt', 'error', 'message'),
    [
        (make_definition_newer, ValueError, 'newer than cps_00001.csv.gz'),
        (point_definition_at_another_set, ValueError, 'does not define the monthly extract'),
        (remove_codebook, FileNotFoundError, 'cps_00001.xml'),
        (add_second_extract, ValueError, '2 extracts share one extract.json'),
    ],
    ids=['later-dry-run', 'wrong-set', 'missing-codebook', 'two-extracts'],
)
def test_a_doubtful_legacy_set_stops_the_backfill_before_anything_moves(
    legacy, corrupt, error, message,
):
    data_dir, lock_path = legacy
    corrupt(data_dir)
    before = tree(data_dir)

    with pytest.raises(error, match=message):
        raw_backfill.backfill(data_dir, lock_path)

    # cps/monthly is checked after acs/core, so an untouched tree proves nothing moved early.
    assert tree(data_dir) == before


def snapshot(root):
    '''Every file's bytes and every directory, so a refused run shows nothing moved or appeared.'''
    directories = sorted(path.relative_to(root).as_posix() for path in root.rglob('*')
                         if path.is_dir())
    return tree(root), directories


@pytest.mark.parametrize(
    'destination',
    ['derived/acs/core/usa_00001.parquet', f'derived/osha/{OSHA_PARQUET}'],
    ids=['ipums-parquet', 'osha-parquet'],
)
def test_a_derived_parquet_already_in_place_stops_the_backfill_with_a_remedy(
    legacy, destination,
):
    data_dir, lock_path = legacy
    existing = data_dir / destination
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b'PAR1 converted by a Stage 1 command')
    legacy_copy = data_dir / 'raw' / destination.removeprefix('derived/')
    before = snapshot(data_dir)

    with pytest.raises(FileExistsError) as raised:
        raw_backfill.backfill(data_dir, lock_path)

    message = str(raised.value)
    assert str(existing) in message
    assert f'delete {legacy_copy} (or {existing}) and re-run' in message
    assert snapshot(data_dir) == before
    assert not paths.manifest_path(data_dir).exists()


def test_a_raw_file_already_at_its_destination_is_never_replaced(legacy):
    data_dir, lock_path = legacy
    existing = data_dir / 'raw/acs/core/usa_00001/usa_00001.xml'
    existing.parent.mkdir()
    existing.write_text('<codeBook>another delivery</codeBook>\n')
    before = snapshot(data_dir)

    with pytest.raises(FileExistsError) as raised:
        raw_backfill.backfill(data_dir, lock_path)

    message = str(raised.value)
    assert str(existing) in message
    assert str(data_dir / 'raw/acs/core/usa_00001.xml') in message
    assert 'resolve it by hand' in message
    assert 'delete' not in message
    assert snapshot(data_dir) == before


def test_a_planned_path_already_recorded_stops_the_backfill_before_anything_moves(legacy):
    data_dir, lock_path = legacy
    path = 'cps/monthly/cps_00001/cps_00001.csv.gz'
    manifest.append_entries(
        paths.manifest_path(data_dir),
        [
            manifest.ManifestEntry(
                path=path,
                sha256='0' * 64,
                size=1,
                retrieved_at='2026-10-12T16:50:59+00:00',
                client='ipumspy',
                client_version='0.8.2',
            )
        ],
    )
    before = snapshot(data_dir)

    with pytest.raises(ValueError, match=f'{path} is already recorded'):
        raw_backfill.backfill(data_dir, lock_path)

    assert snapshot(data_dir) == before


def test_two_moves_to_one_destination_stop_the_backfill_before_anything_moves(
    legacy, monkeypatch,
):
    data_dir, lock_path = legacy
    taken = paths.derived_dir(data_dir, 'acs') / 'core' / 'usa_00001.parquet'
    plan_osha = raw_backfill.plan_osha

    def plan_osha_onto_the_acs_parquet(*args):
        moves, entries = plan_osha(*args)
        return [replace(move, destination=taken) for move in moves], entries

    monkeypatch.setattr(raw_backfill, 'plan_osha', plan_osha_onto_the_acs_parquet)
    before = snapshot(data_dir)

    with pytest.raises(ValueError, match='is the destination of both'):
        raw_backfill.backfill(data_dir, lock_path)

    assert snapshot(data_dir) == before


def test_the_command_reports_what_it_recorded(legacy, cli_runner):
    data_dir, _ = legacy

    result = cli_runner.invoke(raw_backfill.app, ['--data-dir', str(data_dir)])

    assert result.exit_code == 0, result.output
    assert 'recorded acs/core/usa_00001/usa_00001.csv.gz' in result.output
    assert '8 entries appended to' in result.output
