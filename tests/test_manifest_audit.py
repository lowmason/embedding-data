from datetime import UTC, datetime

from embedding_data import cli, manifest, manifest_audit, paths

def test_audit_reports_all_discrepancies_without_mutation(tmp_path):
    root = tmp_path / 'raw'
    root.mkdir()
    files = [root / name for name in ('changed.csv', 'missing.xml', 'ok.zip')]
    for file in files:
        file.write_bytes(b'original')
    entries = [
        manifest.describe_file(
            file,
            root,
            retrieved_at=datetime(2026, 10, 13, tzinfo=UTC),
            client='fixture',
            client_version='1',
        ) for file in files
    ]
    file = paths.manifest_path(tmp_path)
    manifest.append_entries(file, entries)
    before = file.read_bytes()
    files[0].write_bytes(b'modified')
    files[1].unlink()
    (root / 'unrecorded.csv').write_bytes(b'unknown')
    (root / 'extract.part').mkdir()
    (root / 'extract.part/interrupted.csv').write_bytes(b'incomplete')
    (root / '.DS_Store').write_bytes(b'finder')
    issues = manifest_audit.audit(tmp_path)
    assert [(item.path, item.kind) for item in issues] == [
        ('changed.csv', 'hash_mismatch'),
        ('extract.part/interrupted.csv', 'unrecorded'),
        ('missing.xml', 'missing'),
        ('unrecorded.csv', 'unrecorded'),
    ]
    assert file.read_bytes() == before
    assert files[0].read_bytes() == b'modified'

def test_audit_command_exits_nonzero_on_discrepancy(cli_runner, tmp_path):
    (tmp_path / 'raw').mkdir()
    (tmp_path / 'raw/stray.csv').write_bytes(b'x')
    result = cli_runner.invoke(manifest_audit.app, ['--data-dir', str(tmp_path)])
    assert result.exit_code == 1
    assert 'unrecorded' in result.output and 'stray.csv' in result.output
    top_level = cli_runner.invoke(cli.app, ['audit', '--data-dir', str(tmp_path)])
    assert top_level.exit_code == 1
    assert 'unrecorded' in top_level.output and 'stray.csv' in top_level.output


def test_clean_tree_and_duplicate_manifest_entry(tmp_path):
    file = tmp_path / 'raw/ok.csv'
    file.parent.mkdir(parents=True)
    file.write_bytes(b'original')
    entry = manifest.describe_file(
        file,
        file.parent,
        retrieved_at=datetime(2026, 10, 13, tzinfo=UTC),
        client='fixture',
        client_version='1',
    )
    ledger = paths.manifest_path(tmp_path)
    manifest.append_entries(ledger, [entry])
    assert manifest_audit.audit(tmp_path) == []
    ledger.write_text(ledger.read_text() * 2)
    assert manifest_audit.audit(tmp_path) == [
        manifest_audit.AuditIssue('ok.csv', 'duplicate_entry')
    ]
