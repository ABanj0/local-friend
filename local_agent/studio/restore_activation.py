"""Validated next-start selection; the active database is never replaced in place."""
import json
import math
import os
import sqlite3
import time
from contextlib import closing

from local_agent.file_ops import atomic_write
from local_agent.review import fingerprint, signature
from local_agent.safety import Denied, Stopped
from local_agent.studio import backups, restores
from local_agent.studio.migrations import SCHEMA_VERSION
from local_agent.studio.state_owner import (
    POINTER,
    checked_path,
    database_path,
    read_pointer,
    state_policy,
)

FIELDS = {'version', 'id', 'backup', 'backup_sha256', 'database_sha256', 'bytes', 'original_store_id',
          'store_id', 'rollback', 'rollback_sha256', 'schema_version', 'created', 'activated'}
TIMEOUT = 30


def ready(config, ident, expected_sha256):
    deadline = time.monotonic() + TIMEOUT
    if (not isinstance(ident, str) or not restores.IDENT.fullmatch(ident)
            or not isinstance(expected_sha256, str) or not restores.DIGEST.fullmatch(expected_sha256)):
        raise ValueError('Select a prepared restore and its exact database SHA-256')
    marker = checked_path(config, f'restore-staging/{ident}/ready.json')
    marker_version = fingerprint(marker, 4096)
    if marker_version is None:
        raise ValueError('Restore preparation is not ready')
    with marker.open('rb') as source:
        if signature(os.fstat(source.fileno())) != marker_version[1:-1]:
            raise Denied('Restore preparation changed')
        raw = source.read(4097)
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError('Restore preparation metadata is invalid') from None
    if (not isinstance(value, dict) or set(value) != FIELDS
            or type(value['version']) is not int or value['version'] != 1
            or type(value['schema_version']) is not int or value['schema_version'] != SCHEMA_VERSION
            or type(value['bytes']) is not int or not 0 < value['bytes'] <= backups.MAX_BYTES
            or type(value['created']) not in {int, float} or not math.isfinite(value['created']) or value['created'] <= 0
            or value['activated'] is not False or value['id'] != ident
            or any(not isinstance(value[key], str) or not restores.IDENT.fullmatch(value[key])
                   for key in ('id', 'backup', 'store_id', 'original_store_id', 'rollback'))
            or any(not isinstance(value[key], str) or not restores.DIGEST.fullmatch(value[key])
                   for key in ('backup_sha256', 'database_sha256', 'rollback_sha256'))
            or value['database_sha256'] != expected_sha256 or value['store_id'] == value['original_store_id']):
        raise ValueError('Restore preparation metadata is invalid or changed')
    target = checked_path(config, f'restore-staging/{ident}/studio.sqlite3')
    for suffix in ('-wal', '-shm', '-journal'):
        if checked_path(config, f'restore-staging/{ident}/studio.sqlite3{suffix}').exists():
            raise Denied('Restore preparation has journal companions; prepare a fresh copy')
    version = fingerprint(target, backups.MAX_BYTES)
    if version is None or version[-1] != expected_sha256 or version[-3] != value['bytes']:
        raise Denied('Restored database changed; prepare a fresh copy')
    try:
        with closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True, timeout=.2)) as db:
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            if restores.validate_schema(db) != value['store_id']:
                raise Denied('Restored database identity changed')
    except sqlite3.Error:
        raise ValueError('Restored database validation failed') from None
    if fingerprint(target, backups.MAX_BYTES) != version or fingerprint(marker, 4096) != marker_version:
        raise Denied('Restore preparation changed during validation')
    if time.monotonic() >= deadline:
        raise TimeoutError('Restore validation deadline exceeded')
    return value, target, version, marker, marker_version


def activate(manager, owner, ident, expected_sha256, *, confirmed=False, require_restart):
    if confirmed is not True:
        raise Denied('Confirm restoring Studio data and restarting the backend')
    with manager.lock:
        owner.assert_owned()
        if manager.running or manager.shutdown_requested.is_set() or manager.restore_pending.is_set():
            raise ValueError('Finish all owned tasks before restoring; backend must not be shutting down')
        policy = state_policy(manager.config)
        def check_stop():
            try:
                policy.check_stop()
            except Stopped:
                raise Denied('Restore is unavailable while emergency stop is latched') from None

        check_stop()
        current = database_path(manager.config)
        if current != manager.store.path:
            raise Denied('Studio state selection changed; restart before restoring')
        manifest, target, target_version, marker, marker_version = ready(manager.config, ident, expected_sha256)
        if current == target:
            raise ValueError('This restored state is already selected')
        pointer = checked_path(manager.config, POINTER)
        previous = fingerprint(pointer, 4096)
        # A fresh rollback is made after request draining, even if preparation was old.
        rollback = backups.create(manager, confirmed=True)
        if fingerprint(target, backups.MAX_BYTES) != target_version or fingerprint(marker, 4096) != marker_version:
            raise Denied('Restore preparation changed before activation')
        owner.assert_owned()
        check_stop()
        selection = {'version': 1, 'generation': ident, 'store_id': manifest['store_id'],
                     'rollback': rollback['id'], 'rollback_sha256': rollback['sha256']}
        # From publication intent onward, any error is an uncertain selection. Quiesce
        # old APIs and require restart; never blindly roll back a possibly published file.
        manager.restore_pending.set()
        require_restart()
        atomic_write(policy, POINTER, json.dumps(selection, sort_keys=True), pointer, previous)
        if read_pointer(manager.config) != selection:
            raise Denied('Restore selection needs attention; restart before further work')
        return {**selection, 'restart_required': True, 'original_retained': True}
