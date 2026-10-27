"""Bounded UTC interval inspections; only active while the owned Studio runtime lives."""
import copy
import hashlib
import json
import threading
import uuid

from local_agent.safety import Denied, Policy
from local_agent.studio import inspection, model_probe, work_queue
from local_agent.studio.journal import scope_key
from local_agent.studio.time_zones import TIME_ZONES
from local_agent.studio.work_queue import WorkQueue, clock_ms, instant, require

MAX_SCHEDULES = 50
PAUSE_KEY = 'interval_scheduler_paused'
MIN_INTERVAL = 60_000
MAX_INTERVAL = 30 * 86400_000


def timing(next_ms, interval, stamp, misfire):
    """Elapsed UTC slots; skip discards missed slots, coalesce emits the most recent one."""
    require(type(interval) is int and MIN_INTERVAL <= interval <= MAX_INTERVAL)
    instant(next_ms)
    instant(stamp)
    require(misfire in {'skip', 'coalesce'})
    if stamp < next_ms:
        return None, next_ms
    missed = (stamp - next_ms) // interval
    due = next_ms + missed * interval
    future = due + interval
    instant(future)
    return (None if missed and misfire == 'skip' else due), future


def load(db, ident):
    require(work_queue.hex_id(ident))
    row = db.execute('SELECT id,conversation,CASE WHEN length(cast(payload AS BLOB))<=? THEN payload END AS payload,'
        'sha256,enabled,interval_ms,next_ms,misfire,timezone,status,created_ms FROM interval_schedules WHERE id=?',
        (work_queue.MAX_BYTES, ident)).fetchone()
    if row is None:
        raise KeyError('Schedule not found')
    require(isinstance(row['payload'], str) and hashlib.sha256(row['payload'].encode()).hexdigest() == row['sha256'])
    try:
        data = work_queue.payload(json.loads(row['payload']))
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ValueError('Unsupported interval schedule') from None
    require(type(row['enabled']) is int and row['enabled'] in {0, 1} and row['timezone'] in TIME_ZONES)
    require(isinstance(row['conversation'], str) and 0 < len(row['conversation']) <= 128)
    timing(row['next_ms'], row['interval_ms'], row['created_ms'], row['misfire'])
    require(row['status'] in {'ready', 'disabled', 'input_changed', 'model_unavailable', 'invalid', 'queue_full'})
    return {**dict(row), 'data': data}


class Scheduler:
    def __init__(self, manager, gate, *, clock=None):
        self.manager, self.store, self.config, self.gate = manager, manager.store, manager.config, gate
        self.clock = clock or work_queue.now_ms
        self.queue = WorkQueue(self.store, self.config, manager.event_epoch, clock=self.clock)
        self.closing, self.abort = threading.Event(), threading.Event()
        self.thread = None
        self.error = None
        self.latched = False
        self.tick_lock = threading.Lock()
        self.revision = 0
        from local_agent.studio.watches import Watches
        self.watches = Watches(self)

    def paused(self, db):
        row = db.execute('SELECT value FROM metadata WHERE key=?', (PAUSE_KEY,)).fetchone()
        return self.latched or bool(row and row[0] != '0')

    def guard(self, db=None):
        require(not self.closing.is_set() and not self.manager.shutdown_requested.is_set()
                and not self.manager.restore_pending.is_set())
        work_queue.guard(self.config)
        if db is not None:
            require(not self.paused(db))

    def current(self, row):
        base = Policy(self.config, create=False)
        base.no_links(base.root / row['data']['project'])
        root = base.path(row['data']['project'])
        require(row['data']['store'] == self.store.identity and scope_key(root) == row['data']['scope'])
        config = copy.deepcopy(self.config)
        config['paths']['workspace'] = str(root)
        inspection.observe(Policy(config, create=False), row['data']['files'])

    def create(self, conversation, objective, model, project, files, options, interval_ms, misfire, timezone):
        require(timezone in TIME_ZONES)
        stamp = clock_ms(self.clock())
        timing(stamp, interval_ms, stamp, misfire)
        text = self.queue.prepare(objective, model, project, files, options)
        data = json.loads(text)
        require(data['objective'] == objective)
        ident = uuid.uuid4().hex
        with self.manager.lock, self.store.connection() as db:
            self.guard()
            db.execute('BEGIN IMMEDIATE')
            require(db.execute('SELECT count(*) FROM interval_schedules').fetchone()[0] < MAX_SCHEDULES)
            self.manager.memory.bind(db, conversation, data['scope'])
            db.execute('INSERT INTO interval_schedules VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (ident, conversation, text, hashlib.sha256(text.encode()).hexdigest(), 1,
                        interval_ms, clock_ms(stamp + interval_ms), misfire, timezone, 'ready', stamp))
        return ident

    def enabled(self, ident, value):
        require(type(value) is bool)
        with self.manager.lock, self.store.connection() as db:
            row = load(db, ident)
            if value:
                self.guard()
                self.current(row)
            self.abort.set()  # Invalidates any in-flight preflight, including disable/re-enable races.
            self.revision += 1
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE interval_schedules SET enabled=?,status=?,next_ms=? WHERE id=?',
                       (int(value), 'ready' if value else 'disabled',
                        clock_ms(self.clock() + row['interval_ms']) if value else row['next_ms'], ident))
            if not value:
                db.execute("UPDATE workflow_queue SET state='cancelled',owner=NULL,token_sha256=NULL,expires_ms=NULL "
                    "WHERE id IN (SELECT job FROM schedule_runs WHERE schedule=?) AND task IS NULL AND state IN ('queued','leased')", (ident,))
        return {'enabled': value}

    def set_paused(self, value):
        require(type(value) is bool)
        with self.manager.lock:
            self.abort.set()
            if value:
                self.latched = True  # Even a failed pause receipt must stop automatic admission.
            self.revision += 1
            with self.store.connection() as db:
                if not value:
                    self.guard()
                db.execute('INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                           (PAUSE_KEY, '1' if value else '0'))
            self.latched = value
        return {'paused': value}

    def summary(self):
        with self.manager.lock, self.store.connection() as db:
            rows = list(db.execute('SELECT id FROM interval_schedules ORDER BY created_ms DESC LIMIT ?', (MAX_SCHEDULES,)))
            items = []
            for item in rows:
                if not work_queue.hex_id(item['id']):
                    continue  # Untrusted stored labels cannot be echoed as public identifiers.
                try:
                    row = load(db, item['id'])
                    run = db.execute('SELECT q.id,q.state,q.task,r.due_ms,t.status AS task_status FROM schedule_runs r '
                        'JOIN workflow_queue q ON q.id=r.job LEFT JOIN tasks t ON t.id=q.task WHERE r.schedule=? '
                        'ORDER BY r.due_ms DESC LIMIT 1', (row['id'],)).fetchone()
                    if run:
                        queued = self.bound(db, row, run['id'])
                        run = {**dict(run), 'state': queued['state'], 'task': queued['task'],
                               'task_status': work_queue.task_status(db, queued)}
                    items.append({**{key: row[key] for key in ('id', 'conversation', 'interval_ms', 'next_ms', 'misfire', 'timezone', 'status')},
                        'enabled': bool(row['enabled']), 'project': row['data']['project'],
                        'objective': row['data']['objective'], 'files': row['data']['files'], 'model': row['data']['model'],
                        'last': dict(run) if run else None})
                except (ValueError, TypeError, KeyError):
                    items.append({'id': item['id'], 'enabled': False, 'status': 'invalid'})
            return {'items': items, 'paused': self.paused(db), 'error': self.error,
                    'timezones': sorted(TIME_ZONES), 'running_only': True}

    def advance(self):
        stamp = clock_ms(self.clock())
        with self.manager.lock, self.store.connection() as db:
            self.guard(db)
            db.execute('BEGIN IMMEDIATE')
            rows = list(db.execute('SELECT id FROM interval_schedules WHERE enabled=1 AND next_ms<=? '
                                  'ORDER BY next_ms LIMIT ?', (stamp, MAX_SCHEDULES)))
            for candidate in rows:
                try:
                    row = load(db, candidate['id'])
                    self.current(row)
                except (ValueError, Denied, OSError):
                    db.execute("UPDATE interval_schedules SET enabled=0,status='input_changed' WHERE id=?", (candidate['id'],))
                    continue
                due, future = timing(row['next_ms'], row['interval_ms'], stamp, row['misfire'])
                pending = db.execute("SELECT 1 FROM schedule_runs r JOIN workflow_queue q ON q.id=r.job "
                    "WHERE r.schedule=? AND q.state IN ('queued','leased') LIMIT 1", (row['id'],)).fetchone()
                if due is not None and not pending:
                    key = hashlib.sha256(f"{row['id']}:{due}".encode()).hexdigest()
                    try:
                        queued = work_queue.insert(db, key, row['conversation'], row['payload'], stamp)
                    except ValueError:
                        db.execute("UPDATE interval_schedules SET enabled=0,status='queue_full' WHERE id=?", (row['id'],))
                        continue
                    db.execute('INSERT INTO schedule_runs VALUES (?,?,?)', (queued['id'], row['id'], due))
                db.execute('UPDATE interval_schedules SET next_ms=? WHERE id=?', (future, row['id']))

    def bound(self, db, schedule, job):
        queued = work_queue.load(db, job)
        linked = db.execute('SELECT due_ms FROM schedule_runs WHERE job=? AND schedule=?', (job, schedule['id'])).fetchone()
        require(linked is not None)
        due = instant(linked['due_ms'])
        require(queued['data'] == schedule['data'] and queued['conversation'] == schedule['conversation']
                and queued['request_key'] == hashlib.sha256(f"{schedule['id']}:{due}".encode()).hexdigest())
        return queued

    def check_admission(self, claim, schedule, epoch):
        with self.store.connection() as db:
            self.guard(db)
            require(epoch == (self.manager.admission_epoch, self.revision) and not self.abort.is_set())
            row = load(db, schedule)
            require(row['enabled'] == 1)
            self.current(row)
            self.bound(db, row, claim.job)
            work_queue.match(db, claim, self.clock())

    def dispatch(self):
        manager = self.manager
        with manager.lock, self.store.connection() as db:
            self.guard(db)
            if manager.running:
                return
            self.abort.clear()
            epoch = (manager.admission_epoch, self.revision)
            claim = self.queue.claim(seconds=30, automatic_only=True)
            if claim is None:
                return
            sources = list(db.execute("SELECT 'interval' AS kind,schedule AS id FROM schedule_runs WHERE job=? "
                                      "UNION ALL SELECT 'directory',watch FROM directory_runs WHERE job=?", (claim.job, claim.job)))
            if len(sources) != 1:
                self.queue.release(claim)
                return  # Ambiguous or unlinked private items never become automatic authority.
            kind, schedule = sources[0]['kind'], sources[0]['id']
            checker = self.check_admission if kind == 'interval' else self.watches.check_admission
            request = self.queue.request(claim)
        try:
            checker(claim, schedule, epoch)
            config = {**self.config['model'], **request['options'], 'name': request['model']}
            identity = model_probe.identity(config, self.abort)
            inspection.start(manager, request['conversation'], request['objective'], request['model'],
                request['project'], request['files'], request['options'], queue_claim=claim, preflight=identity,
                admission_check=lambda: checker(claim, schedule, epoch))
        except (ValueError, Denied, OSError):
            with manager.lock:
                try:
                    if manager.running or self.abort.is_set() or self.closing.is_set():
                        self.queue.release(claim, retry=True)
                    else:
                        self.queue.release(claim)
                        with self.store.connection() as db:
                            table = 'interval_schedules' if kind == 'interval' else 'directory_watches'
                            db.execute(f"UPDATE {table} SET enabled=0,status='model_unavailable' WHERE id=?", (schedule,))
                except (ValueError, KeyError):
                    pass  # Committed/cancelled/expired claims cannot be replayed or widened.

    def tick(self):
        if not self.tick_lock.acquire(blocking=False):
            return
        entered = False
        try:
            entered = self.gate.enter()
            if not entered:
                return
            self.advance()
            self.watches.poll()
            self.dispatch()
            self.error = None
        except Exception:  # noqa: BLE001 -- fixed content-free diagnostic, no peer or stored exception text
            self.error = 'Scheduler is waiting or unavailable; review schedules and current Studio state.'
        finally:
            if entered:
                self.gate.leave()
            self.tick_lock.release()

    def start(self):
        require(self.thread is None)

        def loop():
            while not self.closing.wait(.5):
                self.tick()

        self.thread = threading.Thread(target=loop, name='studio-intervals', daemon=True)
        try:
            self.thread.start()
        except BaseException:
            self.thread = None
            raise

    def stop(self):
        self.closing.set()
        self.abort.set()
        if self.thread:
            self.thread.join(12)
            if self.thread.is_alive():
                raise OSError('Scheduler cleanup is incomplete; state ownership must be retained')
