from dataclasses import replace
from pathlib import Path

import httpx
import polars as pl
import pytest
from fastexcel import FastExcelError
from geography_fixtures import fixture_registry, originals, seed_geography_tree

from embedding_data import geography_references as gr
from embedding_data import manifest, paths

def test_import_idempotence_pins_and_proxy_provenance(tmp_path):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    file = files['states_2025']
    dest = gr.import_reference(tmp_path, 'states_2025', file, registry=registry)
    before = paths.manifest_path(tmp_path).read_bytes()
    assert gr.import_reference(tmp_path, 'states_2025', file, registry=registry) == dest
    assert dest.read_bytes() == file.read_bytes()
    assert paths.manifest_path(tmp_path).read_bytes() == before
    entry = manifest.entry_for(paths.manifest_path(tmp_path), dest)
    assert entry.proxies == ('retrieved_at',)
    assert entry.client == 'manual-import'
    assert entry.source_url == registry['states_2025'].url
    conflict = tmp_path / 'different.xlsx'
    conflict.write_bytes(b'different bytes')
    with pytest.raises(ValueError):
        gr.import_reference(tmp_path, 'states_2025', conflict, registry=registry)


@pytest.mark.parametrize('defect', ['changed', 'missing', 'symlink', 'partial'])
def test_manifested_original_defects_fail_before_http(tmp_path, monkeypatch, defect):
    registry = seed_geography_tree(tmp_path)
    file = gr.reference_path(tmp_path, registry['cbsa_2023'])
    if defect == 'changed':
        file.write_bytes(b'changed')
    elif defect == 'missing':
        file.unlink()
    elif defect == 'symlink':
        file.unlink()
        file.symlink_to(tmp_path / 'absent')
    else:
        file.with_name(file.name + '.part').write_bytes(b'occupied')
    monkeypatch.setattr(gr, 'make_client', lambda: pytest.fail('HTTP reached before preflight'))
    with pytest.raises((ValueError, FileNotFoundError)):
        gr.acquire(tmp_path, registry=registry)


def test_unrecorded_destination_and_ancestor_symlink_are_refused(tmp_path):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    dest = gr.reference_path(tmp_path, registry['states_2025'])
    dest.parent.mkdir(parents=True)
    dest.write_bytes(files['states_2025'].read_bytes())
    with pytest.raises(ValueError, match='provenance'):
        gr.acquire(tmp_path, registry=registry)
    dest.unlink()
    dest.parent.rmdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    dest.parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        gr.acquire(tmp_path, registry=registry)


def test_cached_acquisition_has_zero_http_and_offline_reads(tmp_path, monkeypatch):
    registry = seed_geography_tree(tmp_path)
    monkeypatch.setattr(
        gr, 'make_client', lambda: pytest.fail('cached acquisition needs no client'))
    assert len(gr.acquire(tmp_path, registry=registry)) == 4
    assert gr.read_sources(tmp_path, registry=registry)['hud'].height == 12


def test_acquisition_uses_registered_urls_and_missing_hud_blocks_first(tmp_path, monkeypatch):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    requests = []

    def respond(request):
        requests.append(str(request.url))
        kind = next(k for k, r in registry.items() if r.url == str(request.url))
        payload = files[kind].read_bytes()
        return httpx.Response(200, headers={'Content-Length': str(len(payload))},
                              stream=httpx.ByteStream(payload))

    monkeypatch.setattr(
        gr, 'make_client', lambda: httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ValueError, match='import-reference hud_2025q4'):
        gr.acquire(tmp_path, registry=registry)
    assert requests == []
    gr.import_reference(tmp_path, 'hud_2025q4', files['hud_2025q4'], registry=registry)
    gr.acquire(tmp_path, registry=registry)
    assert requests == [r.url for k, r in registry.items() if k != 'hud_2025q4']
    assert all(manifest.entry_for(paths.manifest_path(tmp_path),
               gr.reference_path(tmp_path, r)).proxies == ()
               for k, r in registry.items() if k != 'hud_2025q4')


def test_invalid_original_is_validated_before_publication(tmp_path):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    file = files['cbsa_2023']
    file.write_bytes(b'invalid workbook')
    registry['cbsa_2023'] = replace(registry['cbsa_2023'],
                                  sha256=manifest.sha256_file(file), size=file.stat().st_size)
    with pytest.raises((FastExcelError, pl.exceptions.PolarsError)):
        gr.import_reference(tmp_path, 'cbsa_2023', file, registry=registry)
    assert not gr.reference_path(tmp_path, registry['cbsa_2023']).exists()
    assert not paths.manifest_path(tmp_path).exists()


def test_hud_geoid_variant_preserves_logical_workbook_basename(tmp_path):
    from code_fixtures import write_xlsx

    files = originals(tmp_path / 'originals')
    alias = tmp_path / 'browser_download.xlsx'
    write_xlsx(alias, [['ZIP', 'GEOID', 'BUS_RATIO'], ['00001', '01001', '1']])
    files['hud_2025q4'] = alias
    registry = fixture_registry(files)
    dest = gr.import_reference(tmp_path, 'hud_2025q4', alias, registry=registry)
    assert dest.name == 'ZIP-COUNTY_122025.xlsx'
    assert gr.parse_reference(dest, registry['hud_2025q4'])['hud'].item(
        0, 'county_geoid') == '01001'


def test_exclusive_partial_failure_preserves_competing_bytes(tmp_path, monkeypatch):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    dest = gr.reference_path(tmp_path, registry['states_2025'])
    partial = dest.with_name(dest.name + '.part')
    open_path = Path.open

    def occupied(file, mode='r', *args, **kwargs):
        if file == partial and mode == 'xb':
            file.write_bytes(b'competitor')
        return open_path(file, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', occupied)
    with pytest.raises(FileExistsError):
        gr.import_reference(tmp_path, 'states_2025', files['states_2025'], registry=registry)
    assert partial.read_bytes() == b'competitor'
    assert not dest.exists()
