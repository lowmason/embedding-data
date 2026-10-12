'''Data locations under one root: immutable raw downloads, derived Parquet, and previews.

    <data>/raw/manifest.jsonl   one entry per raw file (embedding_data.manifest)
    <data>/raw/<source>/        downloads, kept as delivered
    <data>/derived/<source>/    Parquet converted from raw files
    <data>/preview/<source>/    dry-run extract definitions, overwritten freely
'''

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'


def raw_dir(data_dir: Path, source: str) -> Path:
    return data_dir / 'raw' / source


def derived_dir(data_dir: Path, source: str) -> Path:
    return data_dir / 'derived' / source


def preview_dir(data_dir: Path, source: str) -> Path:
    return data_dir / 'preview' / source


def manifest_path(data_dir: Path) -> Path:
    return data_dir / 'raw' / 'manifest.jsonl'
