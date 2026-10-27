"""Validate and rehearse recovery into fresh state; never replace the active database."""
import hashlib
import json
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
from local_agent.studio import backups
from local_agent.studio.migrations import SCHEMA_VERSION, migrate

MAX_PREPARATIONS = 5
TIMEOUT = 60
IDENT = re.compile(r'[0-9a-f]{32}')
DIGEST = re.compile(r'[0-9a-f]{64}')


def validate_ddl(db):
    """Accept reviewed application DDL only; never install arbitrary triggers/views."""
    db.execute('PRAGMA trusted_schema=OFF')
    with closing(sqlite3.connect(':memory:')) as reference:
        migrate(reference)
        expected = _schema(reference)
    if _schema(db) != expected:
        raise ValueError('Backup contains unsupported schema objects; no schema repair was performed')


def validate_schema(db):
    validate_ddl(db)
    return backups.validate(db)


def _schema(db):
    # Whitespace and SQLite's ALTER TABLE identifier quotes vary in legacy stores.
    return {(kind, name, table, _normalize(sql) if sql else None)
            for kind, name, table, sql in db.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema')}


def _normalize(sql):
    # Preserve string literals exactly; whitespace/quotes inside defaults are data.
    tokens = re.findall(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[^\s'\"]+", sql)
    return ''.join(token[1:-1] if re.fullmatch(r'"[A-Za-z_][A-Za-z_0-9]*"', token) else token for token in tokens)


def prepare(manager, backup, expected_sha256, *, confirmed=False):
    if confirmed is not True:
        raise Denied('Confirm preparing private restored data and a rollback snapshot')
    if (not isinstance(backup, str) or not IDENT.fullmatch(backup)
            or not isinstance(expected_sha256, str) or not DIGEST.fullmatch(expected_sha256)):
        raise ValueError('Select a backup ID and its exact SHA-256')
    with manager.lock:
        if manager.running or manager.shutdown_requested.is_set() or manager.restore_pending.is_set():
            raise ValueError('Finish all owned tasks before preparing restore; backend must not be shutting down')
        config = {**manager.config, 'paths': {**manager.config['paths'],
                                            'workspace': manager.config['paths']['state']}}
        policy = Policy(config, create=False)
        deadline = time.monotonic() + TIMEOUT

        def budget():
            try:
                policy.check_stop()
            except Stopped:
                raise Denied('Restore preparation is unavailable while emergency stop is latched') from None
            if manager.shutdown_requested.is_set() or time.monotonic() >= deadline:
                raise TimeoutError('Restore preparation deadline exceeded or backend is shutting down')

        budget()
        source = policy.path(f'backups/{backup}.sqlite3', write=True)
        if not source.is_file():
            raise KeyError('Backup not found')
        for suffix in ('-wal', '-shm', '-journal'):
            companion = policy.path(f'backups/{backup}.sqlite3{suffix}', write=True)
            if companion.exists():
                raise Denied('Select a standalone backup without journal companion files')
        version = fingerprint(source, backups.MAX_BYTES)
        if version[-1] != expected_sha256:
            raise Denied('Backup changed; select and review its current hash')
        parent = policy.path('restore-staging', write=True)
        parent.mkdir(exist_ok=True)
        if len(list(islice(parent.iterdir(), MAX_PREPARATIONS))) >= MAX_PREPARATIONS:
            raise ValueError('Restore staging is full (5 entries); manage saved preparations before continuing')
        ident = uuid.uuid4().hex
        root = parent / ident
        root.mkdir()  # A late existing preparation is never replaced.
        directory = root.stat()
        owned = {}
        complete = False

        def current_root():
            policy.no_links(root)
            info = root.stat()
            if (info.st_dev, info.st_ino) != (directory.st_dev, directory.st_ino):
                raise Denied('Restore staging directory changed')

        def new_file(name, data=b''):
            current_root()
            path = root / name
            with path.open('xb') as stream:
                info = os.fstat(stream.fileno())
                owned[name] = (info.st_dev, info.st_ino)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            return path

        def checked_file(name):
            current_root()
            path = root / name
            policy.no_links(path)
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or (info.st_dev, info.st_ino) != owned[name]):
                raise Denied('Restore staging file changed')
            return path

        def sql_budget():
            # Exceptions in SQLite callbacks become a bounded DatabaseError.
            budget()
            return 0

        try:
            target = new_file('studio.sqlite3')
            # Closed standalone backups can be copied through checked file descriptors.
            # SQLite never opens the source pathname a second time after its hash review.
            with source.open('rb') as src, target.open('rb+') as dst:
                if signature(os.fstat(src.fileno())) != version[1:-1]:
                    raise Denied('Backup file identity changed before copying')
                target_info = os.fstat(dst.fileno())
                if (target_info.st_dev, target_info.st_ino) != owned['studio.sqlite3']:
                    raise Denied('Restore staging file changed')
                copied, observed = 0, hashlib.sha256()
                while chunk := src.read(65536):
                    budget()
                    copied += len(chunk)
                    if copied > backups.MAX_BYTES:
                        raise ValueError('Restore preparation exceeds 512 MiB')
                    observed.update(chunk)
                    dst.write(chunk)
                dst.flush()
                os.fsync(dst.fileno())
                if signature(os.fstat(src.fileno())) != version[1:-1] or observed.hexdigest() != expected_sha256:
                    raise Denied('Backup changed while copying')
            checked_file('studio.sqlite3')
            with closing(sqlite3.connect(target.as_uri() + '?mode=rw', uri=True, timeout=.2)) as dst:
                dst.set_progress_handler(sql_budget, 1000)
                original_id = validate_schema(dst)  # Reject hostile schema before the first data mutation.
                dst.execute('PRAGMA journal_mode=DELETE')
                new_store_id = uuid.uuid4().hex
                dst.execute("UPDATE metadata SET value=? WHERE key='store_id'", (new_store_id,))
                dst.commit()
                if validate_schema(dst) != new_store_id:
                    raise ValueError('Restored store identity was not published')
            budget()
            if fingerprint(source, backups.MAX_BYTES) != version:
                raise Denied('Backup changed during restore preparation')
            target = checked_file('studio.sqlite3')
            with target.open('rb+') as stream:
                before = os.fstat(stream.fileno())
                if (before.st_dev, before.st_ino) != owned['studio.sqlite3']:
                    raise Denied('Restore staging file changed')
                digest = hashlib.sha256()
                while chunk := stream.read(65536):
                    budget()
                    digest.update(chunk)
                os.fsync(stream.fileno())
                if signature(before) != signature(os.fstat(stream.fileno())):
                    raise Denied('Restored database changed while hashing')
            if signature(before) != signature(checked_file('studio.sqlite3').lstat()):
                raise Denied('Restored database changed while hashing')
            # A failed rollback snapshot must prevent a preparation from becoming ready.
            rollback = backups.create(manager, confirmed=True)
            budget()
            manifest = {'version': 1, 'id': ident, 'backup': backup, 'backup_sha256': expected_sha256,
                        'database_sha256': digest.hexdigest(), 'bytes': before.st_size,
                        'original_store_id': original_id, 'store_id': new_store_id,
                        'rollback': rollback['id'], 'rollback_sha256': rollback['sha256'],
                        'schema_version': SCHEMA_VERSION, 'created': time.time(), 'activated': False}
            new_file('ready.json', json.dumps(manifest, sort_keys=True).encode('utf-8'))
            checked_file('ready.json')
            checked_file('studio.sqlite3')
            complete = True
            return manifest
        except sqlite3.Error:
            # Untrusted schema/parser diagnostics must never become displayed log data.
            raise ValueError('Restore database validation or copy failed') from None
        finally:
            if not complete:
                # No recursive cleanup: preserve unknown files/replacements for inspection.
                try:
                    current_root()
                except (OSError, Denied):
                    pass
                else:
                    for name, identity in owned.items():
                        try:
                            info = (root / name).lstat()
                            if stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == identity:
                                (root / name).unlink()
                        except FileNotFoundError:
                            pass
                    try:
                        root.rmdir()
                    except OSError:
                        pass  # Unknown entries never authorize deletion.
