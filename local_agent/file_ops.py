"""Same-directory staging and checked publication of approved workspace artifacts."""
import ctypes
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .review import CONFLICT, fingerprint, require_unchanged
from .safety import Denied


@contextmanager
def staging(destination):
    descriptor, name = tempfile.mkstemp(prefix=".local-agent-", suffix=".tmp", dir=destination.parent)
    os.close(descriptor)
    path = Path(name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def parent_identity(path):
    info = path.stat()
    return (str(path), info.st_dev, info.st_ino)


def windows_replace(current, staged):
    from ctypes import wintypes
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    security.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                                        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    security.GetFileSecurityW.restype = wintypes.BOOL
    security.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    security.SetFileSecurityW.restype = wintypes.BOOL
    needed = wintypes.DWORD()
    security.GetFileSecurityW(str(current), 4, None, 0, ctypes.byref(needed))
    if not needed.value:
        raise ctypes.WinError(ctypes.get_last_error())
    descriptor = ctypes.create_string_buffer(needed.value)
    if not security.GetFileSecurityW(str(current), 4, descriptor, needed, ctypes.byref(needed)):
        raise ctypes.WinError(ctypes.get_last_error())
    # Verify permission to retain the exact DACL before changing any file bytes.
    if not security.SetFileSecurityW(str(current), 4, descriptor):
        raise ctypes.WinError(ctypes.get_last_error())
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.ReplaceFileW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]
    api.ReplaceFileW.restype = wintypes.BOOL
    if not api.ReplaceFileW(str(current), str(staged), None, 0, None, None):
        raise ctypes.WinError(ctypes.get_last_error())
    # ReplaceFileW can relabel ACEs as inherited. Restore their reviewed flags too.
    if not security.SetFileSecurityW(str(current), 4, descriptor):
        raise ctypes.WinError(ctypes.get_last_error())


def publish(policy, path, staged, destination, version, parent):
    current = policy.path(path, write=True)
    require_unchanged(str(destination), str(current))
    require_unchanged(parent, parent_identity(current.parent))
    require_unchanged(version, fingerprint(current))
    policy.no_links(staged)
    info = staged.lstat()
    if staged.parent != current.parent or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise Denied("Invalid staged artifact")
    policy.check_stop()
    if version is None:
        try:
            # Atomic exclusive publication: unlike rename/replace, never replaces a winner.
            os.link(staged, current, follow_symlinks=False)
        except FileExistsError as exc:
            raise Denied(CONFLICT) from exc
    elif os.name == "nt":
        windows_replace(current, staged)
    else:
        os.chmod(staged, current.stat().st_mode & 0o777)
        os.replace(staged, current)


def atomic_write(policy, path, text, destination, version):
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent = parent_identity(destination.parent)
    with staging(destination) as staged:
        with staged.open("wb") as output:
            output.write(text.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        publish(policy, path, staged, destination, version, parent)
