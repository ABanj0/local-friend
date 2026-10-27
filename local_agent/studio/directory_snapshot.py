"""Private bounded directory observations; no timer, persistence, tool or authority."""
import hashlib
import json
import os
import stat
import time
import unicodedata

from local_agent.repository_search import PRIVATE_NAMES, SKIP_DIRS
from local_agent.review import require_unchanged, signature
from local_agent.safety import Denied
from local_agent.studio.journal import digest, label

MAX_ENTRIES = 2000
MAX_FILES = 128
MAX_BYTES = 4 * 1024**2
MAX_FILE = 64000
MAX_DEPTH = 8
MAX_MANIFEST = 64 * 1024 - 2048
TIME_LIMIT = 2


def excluded(parts):
    controls = {'.ssh', '.aws', '.codex', '.agents'}
    return any(part.casefold() in SKIP_DIRS | PRIVATE_NAMES | controls
               or part.casefold().startswith('.env') or part.casefold().endswith(('.pem', '.key')) for part in parts)


def observe(policy, path='.'):
    """A complete fingerprint describes observed approved regular files, not an atomic tree."""
    if (not isinstance(path, str) or label(path, project=True) != path
            or any(unicodedata.category(c).startswith('C') for c in path)):
        raise Denied('Directory observation requires one canonical approved relative directory')
    root = policy.path(path, write=True)
    if excluded(root.relative_to(policy.root).parts) or root.is_relative_to(policy.state):
        raise Denied('Excluded directories cannot be observation scopes')
    initial = root.lstat()
    if not stat.S_ISDIR(initial.st_mode):
        raise ValueError('Directory observation requires an existing directory')
    scope = digest([str(root), initial.st_dev, initial.st_ino])
    stats = {'entries': 0, 'attempted_files': 0, 'files': 0, 'bytes_read': 0}
    skipped = dict.fromkeys(('excluded', 'denied', 'oversized', 'unreadable', 'changed', 'depth', 'nonregular'), 0)
    stack = [(root, 0, signature(initial))]
    directories, versions, files, names = [], [], [], set()
    reason, manifest_bytes = None, 0
    deadline = time.monotonic() + TIME_LIMIT

    def check():
        nonlocal reason
        policy.check_stop()
        if time.monotonic() >= deadline:
            reason = 'time_limit'
        return reason is not None

    while stack and not check():
        directory, depth, expected = stack.pop()
        try:
            relative_directory = directory.relative_to(policy.root).as_posix()
            require_unchanged(directory, policy.path(relative_directory, write=True))
            require_unchanged(expected, signature(directory.lstat()))
            entry_names = set()
            directories.append((directory, expected, entry_names))
            with os.scandir(directory) as entries:
                for entry in entries:
                    if check():
                        break
                    if stats['entries'] >= MAX_ENTRIES:
                        reason = 'entry_limit'
                        break
                    stats['entries'] += 1
                    entry_names.add(entry.name)
                    candidate = directory / entry.name
                    relative = candidate.relative_to(policy.root).as_posix()
                    if excluded((entry.name,)) or candidate.is_relative_to(policy.state):
                        skipped['excluded'] += 1
                        continue
                    if label(relative) != relative or any(unicodedata.category(c).startswith('C') for c in relative):
                        skipped['denied'] += 1
                        continue
                    try:
                        info = candidate.lstat()  # Windows DirEntry.stat may omit real identity/link counts.
                        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or (
                                stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
                            skipped['denied'] += 1
                            continue
                        current = policy.path(relative, write=True)
                        require_unchanged(candidate, current)
                        if stat.S_ISDIR(info.st_mode):
                            if depth >= MAX_DEPTH:
                                skipped['depth'] += 1
                            else:
                                stack.append((current, depth + 1, signature(info)))
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            skipped['nonregular'] += 1
                            continue
                        if info.st_size > MAX_FILE:
                            skipped['oversized'] += 1
                            continue
                        if stats['attempted_files'] >= MAX_FILES:
                            reason = 'file_limit'
                            break
                        if info.st_size > MAX_BYTES - stats['bytes_read']:
                            reason = 'byte_limit'
                            break
                        stats['attempted_files'] += 1
                        with current.open('rb') as source:
                            require_unchanged(signature(info), signature(os.fstat(source.fileno())))
                            raw = source.read(min(MAX_FILE + 1, MAX_BYTES - stats['bytes_read']))
                            stats['bytes_read'] += len(raw)
                            require_unchanged(signature(info), signature(os.fstat(source.fileno())))
                        require_unchanged(current, policy.path(relative, write=True))
                        require_unchanged(signature(info), signature(current.lstat()))
                        if len(raw) != info.st_size:
                            raise Denied('Directory observation changed during read')
                        if relative.casefold() in names:
                            skipped['changed'] += 1
                            continue
                        item = {'path': relative, 'version': digest(signature(info)), 'sha256': hashlib.sha256(raw).hexdigest()}
                        size = len(json.dumps(item, sort_keys=True, ensure_ascii=True).encode()) + 1
                        if manifest_bytes + size > MAX_MANIFEST:
                            reason = 'manifest_limit'
                            break
                        manifest_bytes += size
                        names.add(relative.casefold())
                        files.append(item)
                        versions.append((current, signature(info)))
                        stats['files'] += 1
                    except Denied:
                        skipped['denied'] += 1
                        skipped['changed'] += 1
                    except OSError:
                        skipped['unreadable'] += 1
        except Denied:
            skipped['changed'] += 1
        except OSError:
            skipped['unreadable'] += 1

    # Directory timestamps can be unchanged despite additions. Re-enumerate names
    # without opening new entries, sharing the original time/entry/STOP budgets.
    for directory, expected, entry_names in directories:
        if check():
            break
        try:
            require_unchanged(directory, policy.path(directory.relative_to(policy.root).as_posix(), write=True))
            require_unchanged(expected, signature(directory.lstat()))
            observed_names = set()
            with os.scandir(directory) as entries:
                for entry in entries:
                    if check():
                        break
                    if stats['entries'] >= MAX_ENTRIES:
                        reason = 'entry_limit'
                        break
                    stats['entries'] += 1
                    observed_names.add(entry.name)
            if observed_names != entry_names:
                skipped['changed'] += 1
            require_unchanged(directory, policy.path(directory.relative_to(policy.root).as_posix(), write=True))
            require_unchanged(expected, signature(directory.lstat()))
        except (Denied, OSError):
            skipped['changed'] += 1

    for target, expected in versions:
        if check():
            break
        try:
            require_unchanged(target, policy.path(target.relative_to(policy.root).as_posix(), write=True))
            require_unchanged(expected, signature(target.lstat()))
        except (Denied, OSError):
            skipped['changed'] += 1
    complete = not (reason or any(skipped[key] for key in ('oversized', 'unreadable', 'changed', 'depth')))
    files.sort(key=lambda item: item['path'])
    return {'version': 1, 'scope': scope, 'files': files, 'fingerprint': digest([scope, files]) if complete else None,
            'complete': complete, 'stop_reason': reason or ('skipped_inputs' if not complete else None),
            'counts': stats, 'skipped': skipped,
            'limits': {'entries': MAX_ENTRIES, 'files': MAX_FILES, 'bytes': MAX_BYTES, 'file_bytes': MAX_FILE,
                       'depth': MAX_DEPTH, 'manifest_bytes': MAX_MANIFEST, 'seconds': TIME_LIMIT}}
