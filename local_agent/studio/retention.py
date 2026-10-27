"""Manual, bounded, exact-preview conversation retention; no filesystem deletion."""
import hashlib
import json
import math
import sqlite3
import struct
import time
import uuid

from local_agent.agent import clean
from local_agent.safety import Denied, Policy, Stopped
from local_agent.studio.migrations import SCHEMA_VERSION
from local_agent.studio.restores import validate_ddl

DEFAULT = {'older_than_days': 90, 'keep_recent': 50, 'batch_size': 20}
POLICY_KEY = 'retention_policy_v1'
RECEIPT_KEY = 'retention_last_action_v1'
MAX_ROWS = 50_000
MAX_BYTES = 64 * 1024**2
TIMEOUT = 5
TTL = 300
TERMINAL = "'reported','planned','no_actions','blocked','failed','cancelled','interrupted'"


def validate_policy(value):
    limits = {'older_than_days': (1, 3650), 'keep_recent': (0, 5000), 'batch_size': (1, 50)}
    if (not isinstance(value, dict) or set(value) != set(limits)
            or any(type(value[key]) is not int or not low <= value[key] <= high
                   for key, (low, high) in limits.items())):
        raise ValueError('Retention requires days1–3650, recent0–5000 and batch1–50 as whole numbers')
    return dict(value)


def policy_in(db):
    row = db.execute('SELECT value FROM metadata WHERE key=?', (POLICY_KEY,)).fetchone()
    if row is None:
        return dict(DEFAULT)
    try:
        if len(row[0]) > 1000:
            raise ValueError
        return validate_policy(json.loads(row[0]))
    except (ValueError, TypeError):
        raise ValueError('Stored retention settings are invalid; save reviewed settings before previewing') from None


class Retention:
    def __init__(self, manager):
        self.manager = manager
        self.previews = {}

    def guard(self):
        if self.manager.running or self.manager.shutdown_requested.is_set() or self.manager.restore_pending.is_set():
            raise ValueError('Finish all owned tasks and pending restart before changing retention')
        try:
            Policy(self.manager.config, create=False).check_stop()
        except Stopped:
            raise Denied('Retention is unavailable while emergency stop is latched') from None

    def settings(self):
        with self.manager.store.connection() as db:
            result = {'policy': policy_in(db), 'automatic': False, 'last_action': None}
            row = db.execute('SELECT value FROM metadata WHERE key=?', (RECEIPT_KEY,)).fetchone()
            if row and isinstance(row[0], str) and len(row[0]) <= 4096:
                try:
                    value = json.loads(row[0])
                    if (isinstance(value, dict) and set(value) == {'created', 'counts', 'deleted'}
                            and type(value['deleted']) is int and 1 <= value['deleted'] <= 50
                            and type(value['created']) in {int, float} and math.isfinite(value['created'])
                            and isinstance(value['counts'], dict) and len(value['counts']) <= 24
                            and all(isinstance(key, str) and type(number) is int and 0 <= number <= MAX_ROWS
                                    for key, number in value['counts'].items())):
                        result['last_action'] = value
                except ValueError:
                    pass
            return result

    def save(self, value):
        value = validate_policy(value)
        with self.manager.lock, self.manager.store.connection() as db:
            self.guard()
            db.execute('INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                       (POLICY_KEY, json.dumps(value, sort_keys=True)))
            self.previews.clear()
        return {'policy': value, 'automatic': False}

    def budget(self, db):
        deadline = time.monotonic() + TIMEOUT

        def check():
            self.guard()
            if time.monotonic() >= deadline:
                raise ValueError('Retention processing limit reached; use a smaller batch')

        db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        return check

    def snapshot(self, db, policy, protected, cutoff, check):
        check()
        try:
            validate_ddl(db)
        except ValueError:
            raise Denied('Stored schema requires review; retention cannot delete data') from None
        if (db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION
                or db.execute("SELECT value FROM metadata WHERE key='store_id'").fetchone()[0] != self.manager.store.identity):
            raise Denied('Studio database identity/version changed; restart and preview again')
        exclusions = 'id NOT IN (' + ','.join('?' for _ in protected) + ')' if protected else '1'
        sql = f"""WITH stamps AS (
            SELECT id AS conversation,created AS stamp FROM conversations
            UNION ALL SELECT conversation,created FROM messages
            UNION ALL SELECT conversation,created FROM tasks
            UNION ALL SELECT t.conversation,e.created FROM events e JOIN tasks t ON t.id=e.task
            UNION ALL SELECT conversation,updated FROM goals
            UNION ALL SELECT conversation,created FROM memories
        ), activity AS (SELECT conversation,max(stamp) AS last_activity FROM stamps GROUP BY conversation),
        ranked AS (SELECT c.id,c.title,a.last_activity,c.rowid AS position FROM conversations c
                   JOIN activity a ON a.conversation=c.id),
        recent AS (SELECT id FROM ranked WHERE typeof(last_activity) IN ('real','integer') AND last_activity>=0 AND last_activity<=?
                   ORDER BY last_activity DESC,position DESC LIMIT ?)
        SELECT id,title,last_activity FROM ranked WHERE typeof(last_activity) IN ('real','integer')
          AND last_activity>=0 AND last_activity<=? AND id NOT IN (SELECT id FROM recent) AND {exclusions}
          AND NOT EXISTS(SELECT 1 FROM goals g WHERE g.conversation=ranked.id AND g.status='active')
          AND NOT EXISTS(SELECT 1 FROM attachments a WHERE a.conversation=ranked.id AND a.message IS NULL)
          AND NOT EXISTS(SELECT 1 FROM workflow_queue q WHERE q.conversation=ranked.id AND q.state IN ('queued','leased'))
          AND NOT EXISTS(SELECT 1 FROM interval_schedules s WHERE s.conversation=ranked.id AND s.enabled<>0)
          AND NOT EXISTS(SELECT 1 FROM directory_watches w WHERE w.conversation=ranked.id AND w.enabled<>0)
          AND NOT EXISTS(SELECT 1 FROM tasks t WHERE t.conversation=ranked.id AND t.status NOT IN ({TERMINAL}))
        ORDER BY last_activity,position LIMIT ?"""
        rows = list(db.execute(sql, (cutoff + policy['older_than_days'] * 86400,
                                    policy['keep_recent'], cutoff, *protected, policy['batch_size'] + 1)))
        more = len(rows) > policy['batch_size']
        rows = rows[:policy['batch_size']]
        ids = [row['id'] for row in rows]
        items = [{'id': row['id'], 'title': clean(row['title'][:120]), 'last_activity': row['last_activity']} for row in rows]
        if not ids:
            return {'items': [], 'counts': {'conversations': 0}, 'more': False}, None
        places = ','.join('?' for _ in ids)
        for table in ('attachments', 'memories'):
            inconsistent = db.execute(f"SELECT 1 FROM {table} a JOIN messages m ON m.id=a.message "
                f"WHERE a.conversation<>m.conversation AND (a.conversation IN ({places}) OR m.conversation IN ({places})) LIMIT 1",
                (*ids, *ids)).fetchone()
            if inconsistent:
                raise Denied('Stored source relationships require review; no retention preview was issued')
        if db.execute(f"SELECT 1 FROM tasks t JOIN goals g ON g.id=t.goal WHERE t.conversation<>g.conversation "
                      f"AND (t.conversation IN ({places}) OR g.conversation IN ({places})) LIMIT 1", (*ids, *ids)).fetchone():
            raise Denied('Stored goal relationships require review; no retention preview was issued')
        for reference in ('source_task', 'resumed_by'):
            if db.execute(f'SELECT 1 FROM inspection_checkpoints c JOIN tasks t ON t.id=c.task '
                          f'JOIN tasks linked ON linked.id=c.{reference} WHERE t.conversation<>linked.conversation '
                          f'AND (t.conversation IN ({places}) OR linked.conversation IN ({places})) LIMIT 1', (*ids, *ids)).fetchone():
                raise Denied('Stored checkpoint relationships require review; no retention preview was issued')
        task_scope = f'task IN (SELECT id FROM tasks WHERE conversation IN ({places}))'
        if db.execute(f'SELECT 1 FROM workflow_queue q JOIN tasks t ON t.id=q.task '
                      f'WHERE q.conversation<>t.conversation AND (q.conversation IN ({places}) '
                      f'OR t.conversation IN ({places})) LIMIT 1', (*ids, *ids)).fetchone():
            raise Denied('Stored queue relationships require review; no retention preview was issued')
        memory_scope = f'scope IN (SELECT scope FROM memories WHERE conversation IN ({places}))'
        if db.execute(f'SELECT 1 FROM memory_file_chunks c JOIN memory_file_sources s ON s.id=c.source '
                      f'JOIN memories m ON m.id=c.memory WHERE m.conversation<>s.conversation '
                      f'AND (m.conversation IN ({places}) OR s.conversation IN ({places})) LIMIT 1', (*ids, *ids)).fetchone():
            raise Denied('Stored file memory relationships require review; no retention preview was issued')
        if db.execute(f'SELECT 1 FROM schedule_runs r JOIN workflow_queue q ON q.id=r.job '
                      f'JOIN interval_schedules s ON s.id=r.schedule WHERE q.conversation<>s.conversation '
                      f'AND (q.conversation IN ({places}) OR s.conversation IN ({places})) LIMIT 1', (*ids, *ids)).fetchone():
            raise Denied('Stored schedule relationships require review; no retention preview was issued')
        groups = [(table, f'conversation IN ({places})', ids, '*') for table in
                  ('messages', 'tasks', 'attachments', 'goals', 'memories', 'workflow_queue', 'interval_schedules', 'directory_watches', 'memory_file_sources')]
        groups += [('memory_file_chunks', f'source IN (SELECT id FROM memory_file_sources WHERE conversation IN ({places}))', ids, '*'),
                   ('memory_vectors', f'memory IN (SELECT id FROM memories WHERE conversation IN ({places}))', ids, '*')]
        groups += [('schedule_runs', f'schedule IN (SELECT id FROM interval_schedules WHERE conversation IN ({places}))', ids, '*')]
        if db.execute(f'SELECT 1 FROM directory_runs r JOIN workflow_queue q ON q.id=r.job '
                      f'JOIN directory_watches w ON w.id=r.watch WHERE q.conversation<>w.conversation '
                      f'AND (q.conversation IN ({places}) OR w.conversation IN ({places})) LIMIT 1', (*ids, *ids)).fetchone():
            raise Denied('Stored watch relationships require review; no retention preview was issued')
        groups += [('directory_runs', f'watch IN (SELECT id FROM directory_watches WHERE conversation IN ({places}))', ids, '*')]
        groups += [('conversations', f'id IN ({places})', ids, '*')]
        groups += [(table, task_scope, ids, '*') for table in
                   ('events', 'verifications', 'execution_steps', 'operations', 'inspection_checkpoints')]
        groups += [('memory_domains', memory_scope, ids, '*'),
                   ('conversations', (f'memory_scope IN (SELECT scope FROM memories WHERE conversation IN ({places})) '
                    f'AND id NOT IN ({places})'), (*ids, *ids), 'id,memory_scope,memory_epoch')]
        digest, counts, total_rows, total_bytes = hashlib.sha256(), {}, 0, 0

        def hash_value(value):
            nonlocal total_bytes
            if value is None:
                tag, data = b'n', b''
            elif isinstance(value, bytes):
                tag, data = b'b', value
            elif isinstance(value, str):
                tag, data = b's', value.encode('utf-8')
            elif isinstance(value, int):
                tag, data = b'i', str(value).encode('ascii')
            elif isinstance(value, float):
                tag, data = b'f', struct.pack('>d', value)
            else:
                raise ValueError('Unsupported stored retention value')
            total_bytes += len(data) + 9
            if total_bytes > MAX_BYTES:
                raise ValueError('Retention preview exceeds64MiB; use a smaller batch')
            digest.update(tag + struct.pack('>Q', len(data)))
            digest.update(data)

        for index, (table, where, args, selection) in enumerate(groups):
            check()
            key = 'context_recipients' if selection != '*' else table
            columns = [r[1] for r in db.execute(f'PRAGMA table_info({table})')] if selection == '*' else selection.split(',')
            sizes = '+'.join('coalesce(length(cast("' + column.replace('"', '""') + '" as blob)),0)' for column in columns)
            count, size = db.execute(f'SELECT count(*),coalesce(sum({sizes}),0) FROM {table} WHERE {where}', args).fetchone()
            if total_rows + count > MAX_ROWS or total_bytes + size > MAX_BYTES:
                raise ValueError('Retention preview exceeds row/byte limits; use a smaller batch')
            counts[key] = count
            hash_value(f'{index}:{key}')
            for row in db.execute(f'SELECT rowid,{selection} FROM {table} WHERE {where} ORDER BY rowid', args):
                check()
                total_rows += 1
                for value in row:
                    hash_value(value)
        check()
        return {'items': items, 'counts': counts, 'more': more}, digest.hexdigest()

    def preview(self, protected=()):
        if (not isinstance(protected, (tuple, list)) or len(protected) > 10
                or any(not isinstance(value, str) or not 0 < len(value) <= 128 for value in protected)
                or len(set(protected)) != len(protected)):
            raise ValueError('Protect at most ten distinct conversation IDs')
        with self.manager.lock:
            with self.manager.store.connection() as db:
                self.guard()
                check = self.budget(db)
                db.execute('BEGIN')
                policy = policy_in(db)
                cutoff = time.time() - policy['older_than_days'] * 86400
                try:
                    public, receipt = self.snapshot(db, policy, tuple(protected), cutoff, check)
                except (sqlite3.Error, UnicodeError):
                    raise ValueError('Retention preview could not be validated; no data was deleted') from None
            now = time.monotonic()
            self.previews = {key: value for key, value in self.previews.items() if value['deadline'] > now}
            if not public['items']:
                return {**public, 'id': None, 'expires': None, 'cutoff': cutoff, 'policy': policy}
            if len(self.previews) >= 8:
                raise ValueError('Too many outstanding retention previews; wait for expiry or reuse a current review')
            ident = uuid.uuid4().hex
            self.previews[ident] = {'deadline': now + TTL, 'policy': policy, 'protected': tuple(protected),
                                    'cutoff': cutoff, 'receipt': receipt, 'store': self.manager.store.identity}
            return {**public, 'id': ident, 'expires': time.time() + TTL, 'cutoff': cutoff, 'policy': policy}

    def apply(self, ident, *, confirmed=False):
        if confirmed is not True:
            raise Denied('Confirm deleting the exact retention preview')
        removed = set()
        with self.manager.lock:
            self.guard()
            review = self.previews.get(ident) if isinstance(ident, str) else None
            if review is None or review['deadline'] <= time.monotonic():
                if isinstance(ident, str):
                    self.previews.pop(ident, None)
                raise ValueError('Retention preview is missing or expired; create a fresh preview')
            self.previews.pop(ident)
            try:
                with self.manager.store.connection() as db:
                    check = self.budget(db)
                    db.execute('BEGIN IMMEDIATE')
                    if review['store'] != self.manager.store.identity or policy_in(db) != review['policy']:
                        raise Denied('Retention settings or store changed; create a fresh preview')
                    public, receipt = self.snapshot(db, review['policy'], review['protected'], review['cutoff'], check)
                    if receipt != review['receipt']:
                        raise Denied('Retention data changed; create a fresh preview')
                    for item in public['items']:
                        check()
                        removed.update(self.manager.store.delete_conversation_in(db, item['id']))
                    summary = {'created': time.time(), 'counts': public['counts'], 'deleted': len(public['items'])}
                    db.execute('INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                               (RECEIPT_KEY, json.dumps(summary, sort_keys=True)))
                    check()
            except (sqlite3.Error, OSError):
                self.previews.pop(ident, None)
                raise ValueError('Retention could not confirm completion; refresh history and create a fresh preview before retrying') from None
            self.previews.clear()
            self.manager.discard_events(removed)
            return summary
