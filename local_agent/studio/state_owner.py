"""One backend owner per fixed state root; reviewed restore-generation routing."""
import json
import os
import re
import sqlite3
import stat
from contextlib import closing

from local_agent.captures import lock
from local_agent.review import fingerprint, signature
from local_agent.safety import Denied, Policy

IDENT = re.compile(r'[0-9a-f]{32}')
POINTER = 'studio-current.json'


def state_policy(config):
    return Policy({**config, 'paths': {**config['paths'], 'workspace': config['paths']['state']}}, create=False)


def checked_path(config, relative):
    # Only application constants/validated IDs reach this helper. Startup must still
    # allow inspecting a latched STOP; mutation paths check stop separately.
    policy = state_policy(config)
    target = policy.root / relative
    policy.no_links(target)
    if target.exists() and target.is_file() and target.stat().st_nlink != 1:
        raise Denied('Studio state files cannot be hardlinked')
    return target


class StateOwner:
    def __init__(self, config):
        self.stream = None
        path = checked_path(config, 'studio-owner.lock')
        try:
            stream = path.open('x+b')
        except FileExistsError:
            stream = path.open('r+b')
        try:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or signature(info) != signature(path.lstat())):
                raise Denied('Studio ownership file changed')
            try:
                lock(stream)
            except OSError:
                raise OSError('Another backend owns this Studio state; close it before starting another') from None
            stream.seek(0)
            if stream.read(2) not in {b'', b'1'}:
                raise Denied('Studio ownership file is invalid; no data was overwritten')
            stream.seek(0)
            stream.write(b'1')
            stream.flush()
            checked_path(config, 'studio-owner.lock')
            if (info.st_dev, info.st_ino) != (path.stat().st_dev, path.stat().st_ino):
                raise Denied('Studio ownership file changed')
            self.stream = stream
            self.path = path
            self.config = config
        except BaseException:
            stream.close()
            raise

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None

    def assert_owned(self):
        if self.stream is None or self.stream.closed:
            raise Denied('Backend no longer owns this Studio state')
        checked_path(self.config, 'studio-owner.lock')
        info = os.fstat(self.stream.fileno())
        current = self.path.stat()
        if info.st_nlink != 1 or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
            raise Denied('Studio ownership identity changed')


def read_pointer(config):
    path = checked_path(config, POINTER)
    version = fingerprint(path, 4096)
    if version is None:
        return None
    with path.open('rb') as stream:
        if signature(os.fstat(stream.fileno())) != version[1:-1]:
            raise Denied('Studio state selection changed')
        raw = stream.read(4097)
    if fingerprint(path, 4096) != version:
        raise Denied('Studio state selection changed')
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError('Studio state selection is invalid; original data is retained') from None
    required = {'version', 'generation', 'store_id', 'rollback', 'rollback_sha256'}
    if (not isinstance(data, dict) or set(data) != required or type(data['version']) is not int
            or data['version'] != 1
            or any(not isinstance(data[key], str) or not IDENT.fullmatch(data[key])
                   for key in ('generation', 'store_id', 'rollback'))
            or not isinstance(data['rollback_sha256'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', data['rollback_sha256'])):
        raise ValueError('Studio state selection is invalid; original data is retained')
    return data


def database_path(config):
    pointer = read_pointer(config)
    if pointer is None:
        return checked_path(config, 'studio.sqlite3')
    path = checked_path(config, f'restore-staging/{pointer["generation"]}/studio.sqlite3')
    if not path.is_file():
        raise ValueError('Selected restored data is missing; original database and backups are retained')
    for suffix in ('-wal', '-shm', '-journal'):
        checked_path(config, f'restore-staging/{pointer["generation"]}/studio.sqlite3{suffix}')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=.2)) as db:
        db.execute('PRAGMA trusted_schema=OFF')
        row = db.execute("SELECT value FROM metadata WHERE key='store_id'").fetchone()
        if row is None or row[0] != pointer['store_id']:
            raise ValueError('Selected restored data identity changed; original data is retained')
    return path
