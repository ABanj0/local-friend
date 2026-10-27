"""Explicit bounded file excerpts. Saved snapshots are data, never execution authority."""
import copy
import hashlib
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass

from local_agent.coding import Coding
from local_agent.repository_search import PRIVATE_NAMES, SKIP_DIRS
from local_agent.review import fingerprint, require_unchanged, signature
from local_agent.safety import Denied, Policy, Stopped, redact

UNSET = object()
MAX_FILE = 64000
MAX_SOURCES = 16
MAX_CHUNKS = 80
CHUNK_CHARS = 900
VIEW = 'utf8-bom-newlines-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True).encode()).hexdigest()


def chunks(text):
    if (type(text) is not str or not text.strip() or len(text.encode()) > MAX_FILE
            or any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in text)):
        raise ValueError('Source must contain bounded nonempty UTF-8 text without control characters')
    result = []
    for start in range(0, len(text), CHUNK_CHARS):
        end = min(len(text), start + CHUNK_CHARS)
        if not text[start:end].strip():
            continue
        result.append({'text': text[start:end], 'start_char': start, 'end_char': end,
                       'start_line': text.count('\n', 0, start) + 1,
                       'end_line': text.count('\n', 0, end - 1) + 1})
    if len(result) > MAX_CHUNKS:
        raise ValueError('Source exceeds its chunk budget')
    return result


@dataclass(frozen=True)
class SourceReceipt:
    owner: object
    scope: str
    admission: int
    records: tuple
    signatures: tuple
    layouts: tuple
    fresh: bool = True


class MemorySources:
    def __init__(self, manager):
        self.manager, self.store = manager, manager.store

    @property
    def forbidden(self):
        return getattr(self.manager.memory_index, 'forbidden', ())

    def guard(self, admission=None):
        if self.manager.shutdown_requested.is_set() or self.manager.restore_pending.is_set():
            raise Denied('File memory is unavailable during shutdown or restore')
        self.manager.memory._idle()
        if admission is not None and admission != self.manager.admission_epoch:
            raise Denied('File memory operation was interrupted')

    def policy(self, project):
        scope = self.manager.memory.scope(project)
        config = copy.deepcopy(self.manager.config)
        root = Policy(config, create=False).path(project, write=True)
        config['paths']['workspace'] = str(root)
        return scope, Policy(config, create=False)

    def path(self, policy, path):
        if (type(path) is not str or not 1 <= len(path) <= 240 or redact(path) != path
                or any(secret and secret in path for secret in self.forbidden)):
            raise Denied('Select a bounded, nonprivate project-relative source path')
        target = policy.path(path, write=True)
        relative = target.relative_to(policy.root)
        if target.is_relative_to(policy.state) or any(
                p.casefold() in SKIP_DIRS | PRIVATE_NAMES or p.casefold().startswith('.env') for p in relative.parts):
            raise Denied('Agent state, credentials, caches and dependencies are not memory sources')
        return target, relative.as_posix()

    def capture(self, project, path):
        try:
            scope, policy = self.policy(project)
            target, relative = self.path(policy, path)
            before = fingerprint(target, MAX_FILE)
            if before is None:
                raise FileNotFoundError('Source is missing')
            value = Coding(policy).read(relative)
            require_unchanged(before, fingerprint(self.path(policy, relative)[0], MAX_FILE))
            require_unchanged(before[-1], value['sha256'])
            require_unchanged(scope, self.manager.memory.scope(project))
            text = value['text'].removeprefix('\ufeff')
            if redact(text) != text or any(secret and secret in text for secret in self.forbidden):
                raise Denied('Remove credentials from the complete source before saving excerpts')
            parts = chunks(text)
            return {'scope': scope, 'path': relative, 'sha256': value['sha256'],
                    'version': digest(before[1:]), 'signature': before[1:-1], 'view': VIEW,
                    'chunks': parts}
        except Stopped:
            raise Denied('File memory operation was interrupted') from None
        except UnicodeError:
            raise ValueError('Source must use UTF-8 text encoding') from None

    @staticmethod
    def records(db, scope):
        rows = [dict(r) for r in db.execute('SELECT * FROM memory_file_sources WHERE scope=? ORDER BY id LIMIT ?',
                                           (scope, MAX_SOURCES + 1))]
        if len(rows) > MAX_SOURCES:
            raise ValueError('File memory exceeds its source budget')
        for row in rows:
            if (any(type(row[k]) is not str or not re.fullmatch(r'[0-9a-f]{32}', row[k]) for k in ('id', 'generation'))
                    or any(type(row[k]) is not str or not re.fullmatch(r'[0-9a-f]{64}', row[k]) for k in ('sha256', 'version'))
                    or row['view'] != VIEW or row['state'] not in {'current', 'stale'}
                    or row['reason'] not in {'', 'changed', 'unavailable', 'unsafe'}):
                raise ValueError('File source metadata is invalid; forget or review the saved source')
        return rows

    @staticmethod
    def versions(records):
        return tuple((r['id'], r['generation'], r['state'], r['version'], r['path']) for r in records)

    @staticmethod
    def layout(db, scope, source):
        sizes = db.execute('SELECT length(m.text),length(CAST(m.text AS BLOB)) FROM memory_file_chunks c '
                           'JOIN memories m ON m.id=c.memory AND m.scope=c.scope WHERE c.scope=? AND c.source=? LIMIT ?',
                           (scope, source, MAX_CHUNKS + 1)).fetchall()
        if len(sizes) > MAX_CHUNKS or any(r[0] > CHUNK_CHARS or r[1] > CHUNK_CHARS * 4 for r in sizes):
            raise ValueError('Saved source excerpts exceed their input limits')
        return [tuple(r) for r in db.execute('SELECT c.ordinal,c.start_char,c.end_char,c.start_line,c.end_line,'
            'm.sha256,m.text,m.conversation FROM memory_file_chunks c JOIN memories m ON m.id=c.memory AND m.scope=c.scope '
            'WHERE c.scope=? AND c.source=? ORDER BY c.ordinal LIMIT ?', (scope, source, MAX_CHUNKS + 1))]

    def prepare(self, project):
        """Hash only explicitly saved sources outside the host lock; never scan directories."""
        with self.manager.lock, self.store.connection() as db:
            scope = self.manager.memory.scope(project)
            rows = self.records(db, scope)
            admission = self.manager.admission_epoch
            if rows:
                self.guard()
            layouts = {}
            for row in rows:
                if row['state'] == 'current':
                    try:
                        layouts[row['id']] = self.layout(db, scope, row['id'])
                    except ValueError:
                        layouts[row['id']] = None
        observed, stale = [], []
        deadline = time.monotonic() + 5
        for row in rows:
            if row['state'] != 'current':
                continue
            if time.monotonic() >= deadline:
                raise ValueError('File source check exceeded its time budget')
            try:
                current = self.capture(project, row['path'])
                expected = [(i, p['start_char'], p['end_char'], p['start_line'], p['end_line'],
                    hashlib.sha256(p['text'].encode()).hexdigest(), p['text'], row['conversation'])
                    for i, p in enumerate(current['chunks'])]
                if current['version'] != row['version']:
                    stale.append((row['id'], row['generation'], 'changed'))
                elif layouts[row['id']] != expected:
                    stale.append((row['id'], row['generation'], 'unsafe'))
                else:
                    observed.append((row['path'], current['signature']))
            except Denied:
                stale.append((row['id'], row['generation'], 'unsafe'))
            except (OSError, ValueError):
                stale.append((row['id'], row['generation'], 'unavailable'))
        with self.manager.lock, self.store.connection() as db:
            if rows:
                self.guard(admission)
            if self.manager.memory.scope(project) != scope:
                raise Denied('Project changed during source checking')
            actual = self.records(db, scope)
            if self.versions(actual) != self.versions(rows):
                raise Denied('Saved sources changed during checking; review and retry')
            for ident, layout in layouts.items():
                if layout is not None and self.layout(db, scope, ident) != layout:
                    raise Denied('Saved excerpts changed during source checking')
            for ident, generation, reason in stale:
                db.execute("UPDATE memory_file_sources SET state='stale',reason=? WHERE id=? AND generation=? AND state='current'",
                           (reason, ident, generation))
            actual = self.records(db, scope)
            states = tuple((r['id'], digest(self.layout(db, scope, r['id']))) for r in actual if r['state'] == 'current')
            return SourceReceipt(self, scope, admission, self.versions(actual), tuple(observed), states)

    def cached(self, project):
        """Human inspection during active work; this receipt cannot admit model context."""
        with self.manager.lock, self.store.connection() as db:
            scope = self.manager.memory.scope(project)
            rows = self.records(db, scope)
            layouts = tuple((r['id'], digest(self.layout(db, scope, r['id']))) for r in rows if r['state'] == 'current')
            return SourceReceipt(self, scope, self.manager.admission_epoch, self.versions(rows), (), layouts, False)

    def validate(self, db, project, receipt, *, read_only=False):
        if not isinstance(receipt, SourceReceipt) or receipt.owner is not self:
            raise Denied('A current host-owned file source check is required')
        if not receipt.fresh and not read_only:
            raise Denied('Saved-only file excerpts cannot admit model context; check sources first')
        if self.manager.admission_epoch != receipt.admission or self.manager.memory.scope(project) != receipt.scope:
            raise Denied('File source check was interrupted or changed scope')
        if self.versions(self.records(db, receipt.scope)) != receipt.records:
            raise Denied('Saved sources changed after checking')
        if any(digest(self.layout(db, receipt.scope, ident)) != value for ident, value in receipt.layouts):
            raise Denied('Saved source excerpts changed after checking')
        if receipt.signatures:
            _, policy = self.policy(project)
            for path, before in receipt.signatures:
                try:
                    target, _ = self.path(policy, path)
                    require_unchanged(before, signature(target.lstat()))
                except (OSError, Denied):
                    raise Denied('Source file changed after checking; refresh sources') from None

    def preview(self, project, path):
        with self.manager.lock:
            self.guard()
            admission = self.manager.admission_epoch
        value = self.capture(project, path)
        with self.manager.lock, self.store.connection() as db:
            self.guard(admission)
            existing = db.execute('SELECT generation FROM memory_file_sources WHERE scope=? AND path=?',
                                  (value['scope'], value['path'])).fetchone()
        return {k: value[k] for k in ('path', 'sha256', 'version', 'view', 'chunks')} | {
            'expected_generation': existing[0] if existing else None}

    def import_file(self, project, conversation, path, sha256, version, expected_generation=None, *, confirmed=False):
        if confirmed is not True:
            raise Denied('Confirm saving the selected file as historical project memory')
        if any(type(v) is not str or not re.fullmatch(r'[0-9a-f]{64}', v) for v in (sha256, version)):
            raise ValueError('A fresh source preview hash and resource version are required')
        with self.manager.lock:
            self.guard()
            admission = self.manager.admission_epoch
        value = self.capture(project, path)
        if value['sha256'] != sha256 or value['version'] != version:
            raise Denied('Source changed since preview; request a fresh preview')
        from local_agent.studio.memory import MAX_NOTES, validate_text
        for part in value['chunks']:
            validate_text(part['text'], self.forbidden)
        with self.manager.lock, self.store.connection() as db:
            self.guard(admission)
            db.execute('BEGIN IMMEDIATE')
            require_unchanged(value['scope'], self.manager.memory.scope(project))
            _, policy = self.policy(project)
            require_unchanged(value['signature'], signature(self.path(policy, value['path'])[0].lstat()))
            self.manager.memory.bind(db, conversation, value['scope'])
            old = db.execute('SELECT id,generation FROM memory_file_sources WHERE scope=? AND path=?',
                             (value['scope'], value['path'])).fetchone()
            if (old['generation'] if old else None) != expected_generation:
                raise Denied('Saved source changed since preview; review before replacing its excerpts')
            if old:
                db.execute('DELETE FROM memory_file_sources WHERE id=?', (old['id'],))
            if len(self.records(db, value['scope'])) >= MAX_SOURCES:
                raise ValueError('Project file memory is full; forget a saved source first')
            count = db.execute('SELECT count(*) FROM memories WHERE scope=?', (value['scope'],)).fetchone()[0]
            if count + len(value['chunks']) > MAX_NOTES:
                raise ValueError('Project memory has insufficient room for all source chunks')
            self.manager.memory.bind(db, conversation, value['scope'], attach=True)
            ident, generation = uuid.uuid4().hex, uuid.uuid4().hex
            db.execute('INSERT INTO memory_file_sources VALUES (?,?,?,?,?,?,?,?,?,?,?)', (
                ident, value['scope'], conversation, value['path'], value['sha256'], value['version'], VIEW,
                generation, 'current', '', time.time()))
            for number, part in enumerate(value['chunks']):
                memory = uuid.uuid4().hex
                db.execute('INSERT INTO memories VALUES (?,?,?,?,?,?,?)', (
                    memory, value['scope'], conversation, None, part['text'], hashlib.sha256(part['text'].encode()).hexdigest(), time.time()))
                db.execute('INSERT INTO memory_file_chunks VALUES (?,?,?,?,?,?,?,?)', (
                    value['scope'], memory, ident, number, part['start_char'], part['end_char'], part['start_line'], part['end_line']))
        return {'source': ident, 'generation': generation, 'chunks': len(value['chunks']), 'sha256': sha256,
                'requires_reindex': True}

    def list(self, project):
        with self.manager.lock, self.store.connection() as db:
            scope = self.manager.memory.scope(project)
            return [{k: r[k] for k in ('id', 'conversation', 'path', 'sha256', 'version', 'view', 'generation', 'state', 'reason')}
                    for r in self.records(db, scope)]

    def forget(self, project, ident, *, confirmed=False):
        if confirmed is not True:
            raise Denied('Confirm forgetting this entire saved file and its excerpts')
        if type(ident) is not str or not re.fullmatch(r'[0-9a-f]{32}', ident):
            raise ValueError('Select a saved source ID')
        with self.manager.lock, self.store.connection() as db:
            self.guard()
            scope = self.manager.memory.scope(project)
            if not db.execute('DELETE FROM memory_file_sources WHERE scope=? AND id=?', (scope, ident)).rowcount:
                raise KeyError('Saved file source not found')


def notes(db, scope, *, ident=None, include_stale=False):
    query = '''SELECT m.*,s.id AS file_id,s.path AS file_path,s.sha256 AS file_sha256,s.version AS file_version,
        s.generation AS file_generation,s.state AS file_state,c.start_char,c.end_char,c.start_line,c.end_line
        FROM memories m LEFT JOIN memory_file_chunks c ON c.memory=m.id AND c.scope=m.scope
        LEFT JOIN memory_file_sources s ON s.id=c.source AND s.scope=c.scope WHERE m.scope=?'''
    args = [scope]
    if ident is not None:
        query += ' AND m.id=?'
        args.append(ident)
    if not include_stale:
        query += " AND (s.id IS NULL OR s.state='current')"
    query += ' ORDER BY m.created DESC,m.id LIMIT 1000'
    result = []
    for raw in db.execute(query, args):
        row = dict(raw)
        file = {k.removeprefix('file_'): row.pop(k) for k in list(row) if k.startswith('file_')}
        for key in ('start_char', 'end_char', 'start_line', 'end_line'):
            file[key] = row.pop(key)
        if file['id'] is not None:
            file['view'] = VIEW
            row['file'] = file
        result.append(row)
    return result
