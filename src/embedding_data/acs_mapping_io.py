'''Safe caller-owned staging and atomic no-replacement directory publication.'''

import ctypes
import errno
import os
import re
import sys
from pathlib import Path

DARWIN_AT_FDCWD = -2
DARWIN_RENAME_EXCL = 4
LINUX_AT_FDCWD = -100
LINUX_RENAME_NOREPLACE = 1


def safe_path(file: Path) -> None:
    '''Reject traversal and symlinks, including ancestors above the supplied root.'''
    file = Path(file)
    if '..' in file.parts:
        raise ValueError('unsafe path traversal')
    for component in (file.absolute(), *file.absolute().parents):
        if component.is_symlink():
            raise ValueError('symlink in selected path')


def reserve_run(data_dir: Path, run_id: str) -> tuple[Path, Path]:
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('unsafe run ID')
    root = Path(data_dir) / 'derived/acs/mapping'
    final, staging = root / run_id, root / (run_id + '.part')
    for file in (final, staging):
        safe_path(file)
        if file.exists():
            raise FileExistsError(file)
    root.mkdir(parents=True, exist_ok=True)
    safe_path(root)
    staging.mkdir()
    return final, staging


def publish_directory(staging: Path, final: Path) -> None:
    '''Use native exclusive rename; occupied finals are never replaced.'''
    staging, final = Path(staging), Path(final)
    for file in (staging, final):
        safe_path(file)
    if staging == final or not staging.is_dir():
        raise ValueError('publication requires a distinct staging directory')
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin' and hasattr(libc, 'renameatx_np'):
        rename, cwd, flag = libc.renameatx_np, DARWIN_AT_FDCWD, DARWIN_RENAME_EXCL
    elif sys.platform == 'linux' and hasattr(libc, 'renameat2'):
        rename, cwd, flag = libc.renameat2, LINUX_AT_FDCWD, LINUX_RENAME_NOREPLACE
    else:
        raise OSError(errno.ENOSYS, 'exclusive directory publication unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                       ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    result = rename(cwd, os.fsencode(staging), cwd, os.fsencode(final), flag)
    if result:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(final))
