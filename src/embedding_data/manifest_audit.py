'''Report raw provenance discrepancies without repairing or changing files.'''

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import typer

from embedding_data import manifest, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

@dataclass(frozen=True)
class AuditIssue:
    path: str
    kind: str

def audit(data_dir: Path) -> list[AuditIssue]:
    file = paths.manifest_path(data_dir)
    root = file.parent
    entries = manifest.read_manifest(file)
    counts = Counter(item.path for item in entries)
    issues = [AuditIssue(path, 'duplicate_entry') for path, n in counts.items() if n > 1]
    for item in entries:
        relative = Path(item.path)
        if relative.is_absolute() or '..' in relative.parts:
            issues.append(AuditIssue(item.path, 'invalid_path'))
            continue
        raw = root / relative
        if raw.is_symlink():
            issues.append(AuditIssue(item.path, 'symlink'))
        elif not raw.is_file():
            issues.append(AuditIssue(item.path, 'missing'))
        elif manifest.sha256_file(raw) != item.sha256:
            issues.append(AuditIssue(item.path, 'hash_mismatch'))
        elif raw.stat().st_size != item.size:
            issues.append(AuditIssue(item.path, 'size_mismatch'))
    for raw in root.rglob('*'):
        if raw == file or raw.name == '.DS_Store':
            continue
        if raw.is_file() or raw.is_symlink():
            relative = raw.relative_to(root).as_posix()
            if relative not in counts:
                issues.append(AuditIssue(relative, 'unrecorded'))
    return sorted(set(issues), key=lambda item: (item.path, item.kind))

@app.command()
def main(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')) -> None:
    try:
        issues = audit(data_dir)
    except (OSError, ValueError, TypeError, KeyError) as error:
        typer.echo(f'audit failed: {error}', err=True)
        raise typer.Exit(code=1) from error
    for issue in issues:
        typer.echo(json.dumps(asdict(issue), sort_keys=True))
    typer.echo(f'{len(issues)} raw provenance discrepancies')
    if issues:
        raise typer.Exit(code=1)

if __name__ == '__main__':
    app()
