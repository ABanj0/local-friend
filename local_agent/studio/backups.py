"""Confirmed, bounded SQLite snapshots to fixed application-owned storage.

Backups contain private data. They are not redacted exports or execution checkpoints.
No user/model path, migration, restore, deletion, or automatic retention is accepted here.
"""
import hashlib
import os
import re
import sqlite3
import stat
import time
import uuid
from contextlib import closing
from itertools import islice

from local_agent.review import fingerprint, signature
from local_agent.safety import Denied, Policy, Stopped
from local_agent.studio.migrations import MIGRATIONS, REQUIRED, SCHEMA_VERSION, columns
from local_agent.studio.state_owner import checked_path, database_path

MAX_BYTES = 512 * 1024**2
MAX_BACKUPS = 20
TIMEOUT = 30


def inventory(manager):
    root = checked_path(manager.config, 'backups')
    if not root.exists():
        return {'items': [], 'entries': 0, 'capacity': MAX_BACKUPS, 'incomplete': False}
    paths = list(islice(root.iterdir(), MAX_BACKUPS + 1))
    rows = []
    for path in paths[:MAX_BACKUPS]:
        if not re.fullmatch(r'[0-9a-f]{32}\.sqlite3', path.name):
            continue
        try:
            current = checked_path(manager.config, f'backups/{path.name}')
            info = current.lstat()
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BYTES:
                continue
            rows.append({'id': current.stem, 'filename': current.name, 'bytes': info.st_size,
                         'created': info.st_mtime})
        except (OSError, Denied):
            continue
    return {'items': sorted(rows, key=lambda row: (row['created'], row['id']), reverse=True),
            'entries': len(paths), 'capacity': MAX_BACKUPS, 'incomplete': len(paths) > MAX_BACKUPS}


def inspect(manager, ident):
    if not isinstance(ident, str) or not re.fullmatch(r'[0-9a-f]{32}', ident):
        raise ValueError('Select a backup ID')
    started = time.monotonic()
    path = checked_path(manager.config, f'backups/{ident}.sqlite3')
    for suffix in ('-wal', '-shm', '-journal'):
        if checked_path(manager.config, f'backups/{ident}.sqlite3{suffix}').exists():
            raise Denied('Select a standalone backup without journal companions')
    version = fingerprint(path, MAX_BYTES)
    if version is None:
        raise KeyError('Backup not found')
    if time.monotonic() - started >= TIMEOUT:
        raise TimeoutError('Backup inspection deadline exceeded')
    return {'id': ident, 'filename': path.name, 'bytes': version[-3], 'sha256': version[-1],
            'created': path.stat().st_mtime, 'encrypted': False}


def validate(db):
    """Read-only current-schema checks; never migrate or repair a backup."""
    db.execute('PRAGMA trusted_schema=OFF')
    if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
        raise ValueError('Backup schema version is incompatible')
    history = [tuple(row) for row in db.execute('SELECT version,name FROM schema_migrations ORDER BY version')]
    if history != [(i + 1, name) for i, (name, _) in enumerate(MIGRATIONS)]:
        raise ValueError('Backup migration history is inconsistent')
    for table, expected in REQUIRED.items():
        if not expected <= columns(db, table):
            raise ValueError('Backup schema is incomplete')
    ident = db.execute("SELECT value FROM metadata WHERE key='store_id'").fetchone()
    if not ident or not isinstance(ident[0], str) or len(ident[0]) != 32 or any(c not in '0123456789abcdef' for c in ident[0]):
        raise ValueError('Backup store identity is invalid')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('Backup integrity check failed')
    if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise ValueError('Backup has invalid references')
    return ident[0]


def create(manager, *, confirmed=False):
    if confirmed is not True:
        raise Denied('Confirm saving a private, unencrypted Studio backup')
    with manager.lock:
        if manager.running:
            raise ValueError('Finish or cancel the active task before creating a backup')
        if manager.shutdown_requested.is_set() or manager.restore_pending.is_set():
            raise ValueError('Backend is shutting down')
        # Reuse existing path/link policy, with a narrower root fixed to app state.
        config = {**manager.config, 'paths': {**manager.config['paths'],
                                            'workspace': manager.config['paths']['state']}}
        policy = Policy(config, create=False)
        def check_stop():
            try:
                policy.check_stop()
            except Stopped:
                raise Denied('Backup is unavailable while emergency stop is latched') from None

        check_stop()
        selected = database_path(manager.config)
        relative = selected.relative_to(policy.root)
        source = policy.path(str(relative), write=True)
        if source != manager.store.path or not source.is_file():
            raise Denied('Studio database is not the configured state file')
        for suffix in ('-wal', '-shm', '-journal'):
            policy.path(str(relative) + suffix, write=True)
        root = policy.path('backups', write=True)
        root.mkdir(exist_ok=True)
        if len(list(islice(root.iterdir(), MAX_BACKUPS))) >= MAX_BACKUPS:
            raise ValueError('Backup storage is full (20 entries); manage saved copies before continuing')
        parent = root.stat()
        ident = uuid.uuid4().hex
        destination = root / (ident + '.sqlite3')
        staged = root / ('.' + ident + '.partial')
        owned = None
        deadline = time.monotonic() + TIMEOUT

        def budget():
            check_stop()
            if manager.shutdown_requested.is_set() or time.monotonic() >= deadline:
                raise TimeoutError('Studio backup deadline exceeded or backend is shutting down')

        def progress(status, remaining, total):
            budget()
            if status not in {sqlite3.SQLITE_OK, sqlite3.SQLITE_DONE, sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                raise ValueError('Studio backup failed')
            if total * page_size > MAX_BYTES:
                raise ValueError('Studio backup exceeds 512 MiB')

        def unchanged(path, *, single=True):
            policy.no_links(path)
            info = path.lstat()
            if ((info.st_dev, info.st_ino) != owned or not stat.S_ISREG(info.st_mode)
                    or single and info.st_nlink != 1):
                raise Denied('Backup staging identity changed')

        try:
            with staged.open('xb') as stream:
                owned = (os.fstat(stream.fileno()).st_dev, os.fstat(stream.fileno()).st_ino)
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=.2)) as src:
                page_size = src.execute('PRAGMA page_size').fetchone()[0]
                if src.execute('PRAGMA page_count').fetchone()[0] * page_size > MAX_BYTES:
                    raise ValueError('Studio backup exceeds 512 MiB')
                unchanged(staged)
                with closing(sqlite3.connect(staged.as_uri() + '?mode=rw', uri=True, timeout=.2)) as dst:
                    src.backup(dst, pages=128, progress=progress, sleep=.01)
                    # Standalone output must not depend on WAL/SHM companion files.
                    dst.execute('PRAGMA journal_mode=DELETE')
                    dst.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
                    observed_identity = validate(dst)
                    if observed_identity != manager.store.identity:
                        raise ValueError('Studio backup identity does not match the source')
            budget()
            unchanged(staged)
            digest = hashlib.sha256()
            with staged.open('rb+') as stream:
                before = os.fstat(stream.fileno())
                if (before.st_dev, before.st_ino) != owned:
                    raise Denied('Backup staging identity changed')
                while chunk := stream.read(65536):
                    budget()
                    digest.update(chunk)
                os.fsync(stream.fileno())
                if signature(before) != signature(os.fstat(stream.fileno())):
                    raise Denied('Backup changed while hashing')
            unchanged(staged)
            if signature(before) != signature(staged.lstat()):
                raise Denied('Backup changed while hashing')
            policy.no_links(destination)
            current = root.stat()
            if (parent.st_dev, parent.st_ino) != (current.st_dev, current.st_ino):
                raise Denied('Backup directory changed')
            os.link(staged, destination, follow_symlinks=False)  # Exclusive: never replace a saved copy.
            unchanged(destination, single=False)
            return {'id': ident, 'filename': destination.name, 'bytes': destination.stat().st_size,
                    'sha256': digest.hexdigest(), 'schema_version': SCHEMA_VERSION,
                    'created': time.time(), 'encrypted': False}
        finally:
            # Cleanup only this call's staging entry. Unknown replacements survive.
            if owned is not None:
                try:
                    info = staged.lstat()
                    if (info.st_dev, info.st_ino) == owned and stat.S_ISREG(info.st_mode):
                        staged.unlink()
                except FileNotFoundError:
                    pass
