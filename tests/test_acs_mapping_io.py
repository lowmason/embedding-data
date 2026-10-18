import pytest

from embedding_data import acs_mapping_io as mapping_io
from embedding_data.acs_mapping_io import publish_directory, reserve_run

def test_publication_does_not_replace_a_concurrent_empty_directory(tmp_path):
    staging, final = tmp_path / 'run.part', tmp_path / 'run'
    staging.mkdir()
    (staging / 'report.json').write_text('{}\n')
    final.mkdir()
    with pytest.raises(FileExistsError):
        publish_directory(staging, final)
    assert list(final.iterdir()) == []
    assert (staging / 'report.json').read_text() == '{}\n'


def test_exclusive_publication_succeeds(tmp_path):
    final, staging = reserve_run(tmp_path, 'run')
    (staging / 'report.json').write_text('{}')
    publish_directory(staging, final)
    assert (final / 'report.json').read_text() == '{}'
    assert not staging.exists()


@pytest.mark.parametrize('run_id', ['../bad', '', 'a/b', 'run.part', '/absolute'])
def test_unsafe_ids_are_rejected(tmp_path, run_id):
    with pytest.raises(ValueError):
        reserve_run(tmp_path, run_id)


@pytest.mark.parametrize('name', ['run', 'run.part'])
def test_occupied_paths_are_preserved(tmp_path, name):
    directory = tmp_path / 'derived/acs/mapping' / name
    directory.mkdir(parents=True)
    with pytest.raises((ValueError, FileExistsError)):
        reserve_run(tmp_path, 'run')
    assert directory.is_dir()


def test_symlinked_ancestor_is_rejected(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / 'derived').symlink_to(outside)
    with pytest.raises(ValueError):
        reserve_run(tmp_path, 'run')


def test_unavailable_native_guarantee_fails_closed(tmp_path, monkeypatch):
    staging = tmp_path / 'run.part'
    staging.mkdir()
    monkeypatch.setattr(mapping_io.sys, 'platform', 'unsupported')
    with pytest.raises(OSError):
        publish_directory(staging, tmp_path / 'run')
    assert staging.is_dir()


@pytest.mark.parametrize('platform,symbol,cwd,flag', [
    ('darwin', 'renameatx_np', -2, 4), ('linux', 'renameat2', -100, 1)])
@pytest.mark.parametrize('native_errno', [0, 17, 18, 38])
def test_native_dispatch_and_errors(tmp_path, monkeypatch, platform, symbol, cwd, flag,
                                    native_errno):
    import ctypes
    from types import SimpleNamespace

    calls = []
    def rename(*args):
        calls.append(args)
        ctypes.set_errno(native_errno)
        return -1 if native_errno else 0
    monkeypatch.setattr(mapping_io.sys, 'platform', platform)
    monkeypatch.setattr(mapping_io.ctypes, 'CDLL',
                        lambda *a, **k: SimpleNamespace(**{symbol: rename}))
    staging, final = tmp_path / 'run.part', tmp_path / 'run'
    staging.mkdir()
    if native_errno:
        with pytest.raises(OSError) as error:
            publish_directory(staging, final)
        assert error.value.errno == native_errno
    else:
        publish_directory(staging, final)
    assert calls == [(cwd, bytes(staging), cwd, bytes(final), flag)]
