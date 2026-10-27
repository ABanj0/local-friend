"""Persisted directory-change observations; all execution uses the read-only coordinator."""
import copy
import hashlib
import json
import stat
import unicodedata
import uuid

from local_agent.safety import Denied, Policy
from local_agent.studio import directory_snapshot, probes, work_queue
from local_agent.studio.journal import digest, label, scope_key
from local_agent.studio.work_queue import hex_id, instant, require

MAX_WATCHES = 10
SCAN_MS = 5000
STATES = {'initializing', 'ready', 'debouncing', 'incomplete', 'disabled', 'input_changed',
          'model_unavailable', 'queue_full', 'invalid'}
REASONS = {None, 'entry_limit', 'file_limit', 'byte_limit', 'manifest_limit', 'time_limit', 'skipped_inputs'}


def load(db, ident):
    require(hex_id(ident))
    row = db.execute('SELECT id,conversation,CASE WHEN length(cast(payload AS BLOB))<=? THEN payload END AS payload,'
        'sha256,directory,directory_scope,enabled,debounce_ms,baseline,candidate,candidate_ms,next_ms,'
        'generation,revision,status,created_ms FROM directory_watches WHERE id=?', (work_queue.MAX_BYTES, ident)).fetchone()
    if row is None:
        raise KeyError('Directory watch not found')
    require(isinstance(row['payload'], str) and hashlib.sha256(row['payload'].encode()).hexdigest() == row['sha256'])
    try:
        data = work_queue.payload(json.loads(row['payload']))
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ValueError('Unsupported directory watch') from None
    require(isinstance(row['conversation'], str) and 0 < len(row['conversation']) <= 128)
    require(isinstance(row['directory'], str) and label(row['directory'], project=True) == row['directory'])
    require(hex_id(row['directory_scope'], 64) and row['status'] in STATES)
    require(type(row['enabled']) is int and row['enabled'] in {0, 1})
    require(type(row['debounce_ms']) is int and 1000 <= row['debounce_ms'] <= 60000)
    require(row['baseline'] is None or hex_id(row['baseline'], 64))
    require((row['candidate'] is None and row['candidate_ms'] is None) or
            (hex_id(row['candidate'], 64) and row['candidate'] != row['baseline'] and row['baseline'] is not None))
    if row['candidate'] is not None:
        instant(row['candidate_ms'])
    instant(row['created_ms'])
    instant(row['next_ms'])
    require(all(type(row[key]) is int and 0 <= row[key] < 2**31 - 1 for key in ('generation', 'revision')))
    return {**dict(row), 'data': data}


def observation(value):
    require(isinstance(value, dict) and set(value) == {'scope', 'fingerprint', 'complete', 'stop_reason', 'counts'})
    require(hex_id(value['scope'], 64) and type(value['complete']) is bool and value['stop_reason'] in REASONS)
    require((value['complete'] and hex_id(value['fingerprint'], 64) and value['stop_reason'] is None)
            or (not value['complete'] and value['fingerprint'] is None and value['stop_reason'] is not None))
    counts = value['counts']
    limits = {'entries': directory_snapshot.MAX_ENTRIES, 'attempted_files': directory_snapshot.MAX_FILES,
              'files': directory_snapshot.MAX_FILES, 'bytes_read': directory_snapshot.MAX_BYTES}
    require(isinstance(counts, dict) and set(counts) == set(limits))
    require(all(type(counts[key]) is int and 0 <= counts[key] <= limit for key, limit in limits.items()))
    require(counts['files'] <= counts['attempted_files'] <= counts['entries'])
    return value


def trigger(watch, generation, fingerprint):
    return hashlib.sha256(f'directory:{watch}:{generation}:{fingerprint}'.encode()).hexdigest()


class Watches:
    def __init__(self, scheduler):
        self.scheduler, self.manager, self.store = scheduler, scheduler.manager, scheduler.store

    def directory(self, data, path):
        config = copy.deepcopy(self.manager.config)
        base = Policy(config, create=False)
        base.no_links(base.root / data['project'])
        config['paths']['workspace'] = str(base.path(data['project']))
        policy = Policy(config, create=False)
        require(isinstance(path, str) and label(path, project=True) == path
                and not any(unicodedata.category(c).startswith('C') for c in path))
        root = policy.path(path, write=True)
        if root.is_relative_to(policy.state) or directory_snapshot.excluded(root.relative_to(policy.root).parts):
            raise Denied('Agent state and excluded paths cannot be watched')
        info = root.lstat()
        require(stat.S_ISDIR(info.st_mode))
        return config, digest([str(root), info.st_dev, info.st_ino])

    def current(self, row):
        config, scope = self.directory(row['data'], row['directory'])
        require(row['data']['store'] == self.store.identity and scope == row['directory_scope']
                and scope_key(Policy(config, create=False).root) == row['data']['scope'])
        return config

    def create(self, conversation, objective, model, project, files, options, directory, debounce_ms):
        require(type(debounce_ms) is int and 1000 <= debounce_ms <= 60000)
        text = self.scheduler.queue.prepare(objective, model, project, files, options)
        data = json.loads(text)
        require(data['objective'] == objective)
        _, scope = self.directory(data, directory)
        ident, stamp = uuid.uuid4().hex, instant(self.scheduler.clock())
        with self.manager.lock, self.store.connection() as db:
            self.scheduler.guard()
            self.current({'data': data, 'directory': directory, 'directory_scope': scope})
            db.execute('BEGIN IMMEDIATE')
            require(db.execute('SELECT count(*) FROM directory_watches').fetchone()[0] < MAX_WATCHES)
            self.manager.memory.bind(db, conversation, data['scope'])
            db.execute('INSERT INTO directory_watches VALUES (?,?,?,?,?,?,1,?,NULL,NULL,NULL,?,0,0,?,?)',
                (ident, conversation, text, hashlib.sha256(text.encode()).hexdigest(), directory, scope,
                 debounce_ms, stamp, 'initializing', stamp))
        return ident

    def enabled(self, ident, value):
        require(type(value) is bool)
        with self.manager.lock, self.store.connection() as db:
            row = load(db, ident)
            if value:
                self.scheduler.guard()
                self.current(row)
            self.scheduler.abort.set()
            self.scheduler.revision += 1
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE directory_watches SET enabled=?,status=?,revision=revision+1,'
                       'baseline=CASE WHEN ? THEN NULL ELSE baseline END,candidate=NULL,candidate_ms=NULL,next_ms=? WHERE id=?',
                       (int(value), 'initializing' if value else 'disabled', int(value), instant(self.scheduler.clock()), ident))
            if not value:
                self.cancel_pending(db, ident)
        return {'enabled': value}

    @staticmethod
    def cancel_pending(db, ident):
        db.execute("UPDATE workflow_queue SET state='cancelled',owner=NULL,token_sha256=NULL,expires_ms=NULL "
                   "WHERE id IN (SELECT job FROM directory_runs WHERE watch=?) AND task IS NULL AND state IN ('queued','leased')", (ident,))

    def bound(self, db, row, job):
        queued = work_queue.load(db, job)
        linked = db.execute('SELECT generation,fingerprint FROM directory_runs WHERE job=? AND watch=?', (job, row['id'])).fetchone()
        require(linked is not None and type(linked['generation']) is int and 1 <= linked['generation'] <= row['generation'])
        require(hex_id(linked['fingerprint'], 64) and queued['data'] == row['data'] and queued['conversation'] == row['conversation'])
        require(queued['request_key'] == trigger(row['id'], linked['generation'], linked['fingerprint']))
        return queued

    def check_admission(self, claim, ident, epoch):
        with self.store.connection() as db:
            self.scheduler.guard(db)
            require(epoch == (self.manager.admission_epoch, self.scheduler.revision) and not self.scheduler.abort.is_set())
            row = load(db, ident)
            require(row['enabled'] == 1)
            self.current(row)
            self.bound(db, row, claim.job)
            work_queue.match(db, claim, self.scheduler.clock())

    def accept(self, ident, value, epoch, revision):
        value = observation(value)
        stamp = instant(self.scheduler.clock())
        with self.manager.lock, self.store.connection() as db:
            self.scheduler.guard(db)
            require(epoch == (self.manager.admission_epoch, self.scheduler.revision) and not self.scheduler.abort.is_set())
            db.execute('BEGIN IMMEDIATE')
            row = load(db, ident)
            require(row['enabled'] == 1 and row['revision'] == revision)
            self.current(row)
            require(value['scope'] == row['directory_scope'])
            db.execute('UPDATE directory_watches SET next_ms=? WHERE id=?', (instant(stamp + SCAN_MS), ident))
            if not value['complete']:
                db.execute("UPDATE directory_watches SET candidate=NULL,candidate_ms=NULL,status='incomplete' WHERE id=?", (ident,))
                return
            fingerprint = value['fingerprint']
            if row['baseline'] is None or row['baseline'] == fingerprint:
                db.execute("UPDATE directory_watches SET baseline=?,candidate=NULL,candidate_ms=NULL,status='ready' WHERE id=?", (fingerprint, ident))
            elif row['candidate'] != fingerprint:
                db.execute("UPDATE directory_watches SET candidate=?,candidate_ms=?,status='debouncing' WHERE id=?", (fingerprint, stamp, ident))
            elif stamp - row['candidate_ms'] >= row['debounce_ms']:
                pending = db.execute("SELECT 1 FROM directory_runs r JOIN workflow_queue q ON q.id=r.job "
                    "WHERE r.watch=? AND q.state IN ('queued','leased') LIMIT 1", (ident,)).fetchone()
                if not pending:
                    generation = row['generation'] + 1
                    try:
                        queued = work_queue.insert(db, trigger(ident, generation, fingerprint), row['conversation'], row['payload'], stamp)
                    except ValueError:
                        db.execute("UPDATE directory_watches SET enabled=0,status='queue_full' WHERE id=?", (ident,))
                        return
                    db.execute('INSERT INTO directory_runs VALUES (?,?,?,?)', (queued['id'], ident, generation, fingerprint))
                    db.execute('UPDATE directory_watches SET generation=? WHERE id=?', (generation, ident))
                db.execute("UPDATE directory_watches SET baseline=?,candidate=NULL,candidate_ms=NULL,status='ready' WHERE id=?", (fingerprint, ident))

    def poll(self):
        scheduler = self.scheduler
        with self.manager.lock, self.store.connection() as db:
            scheduler.guard(db)
            if self.manager.running:
                return
            candidate = db.execute('SELECT id FROM directory_watches WHERE enabled=1 AND next_ms<=? '
                                   'ORDER BY next_ms,rowid LIMIT 1', (instant(scheduler.clock()),)).fetchone()
            if candidate is None:
                return
            ident = candidate['id']
            try:
                row = load(db, ident)
                config = self.current(row)
            except (ValueError, Denied, OSError):
                db.execute("UPDATE directory_watches SET enabled=0,status='input_changed' WHERE id=?", (ident,))
                self.cancel_pending(db, ident)
                return
            scheduler.abort.clear()
            epoch, revision = (self.manager.admission_epoch, scheduler.revision), row['revision']
        try:
            value = probes.run('directory', {'config': config, 'path': row['directory']}, scheduler.abort, timeout=4)
            self.accept(ident, value, epoch, revision)
        except (ValueError, Denied, OSError, KeyError):
            with self.manager.lock, self.store.connection() as db:
                if epoch == (self.manager.admission_epoch, scheduler.revision) and not scheduler.abort.is_set():
                    db.execute("UPDATE directory_watches SET next_ms=?,candidate=NULL,candidate_ms=NULL,status='incomplete' "
                               'WHERE id=? AND enabled=1 AND revision=?', (instant(scheduler.clock() + SCAN_MS), ident, revision))

    def summary(self):
        with self.manager.lock, self.store.connection() as db:
            items = []
            invalid = 0
            for candidate in list(db.execute('SELECT id FROM directory_watches ORDER BY created_ms DESC LIMIT ?', (MAX_WATCHES,))):
                if not hex_id(candidate['id']):
                    invalid += 1
                    continue
                try:
                    row = load(db, candidate['id'])
                    last = db.execute('SELECT job,generation FROM directory_runs WHERE watch=? ORDER BY generation DESC LIMIT 1', (row['id'],)).fetchone()
                    queued = self.bound(db, row, last['job']) if last else None
                    items.append({**{key: row[key] for key in ('id', 'conversation', 'directory', 'debounce_ms', 'status', 'generation', 'next_ms')},
                        'enabled': bool(row['enabled']), 'project': row['data']['project'], 'objective': row['data']['objective'],
                        'files': row['data']['files'], 'model': row['data']['model'],
                        'last': {'id': queued['id'], 'state': queued['state'], 'task': queued['task'],
                                 'task_status': work_queue.task_status(db, queued)} if queued else None})
                except (ValueError, TypeError, KeyError):
                    items.append({'id': candidate['id'], 'enabled': False, 'status': 'invalid'})
            return {'items': items, 'paused': self.scheduler.paused(db), 'scan_ms': SCAN_MS,
                    'running_only': True, 'invalid_records': invalid}
