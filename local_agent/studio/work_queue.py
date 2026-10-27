"""Private durable read-only admission leases. No timer, dispatcher or model tool."""
import copy
import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import asdict, dataclass, field

from local_agent.agent import clean
from local_agent.inference import InferenceOptions
from local_agent.observability import hex_id
from local_agent.safety import Denied, Policy, Stopped
from local_agent.studio.inspection import observe, paths
from local_agent.studio.journal import label, scope_key

MAX_BYTES = 65536
MAX_ITEMS = 1000
MAX_TOTAL_BYTES = 64 * 1024**2
MAX_SCAN = 32
STATES = {'queued', 'leased', 'admitted', 'blocked', 'cancelled'}


def require(condition):
    if not condition:
        raise ValueError('Invalid or stale workflow queue record/claim')


def now_ms():
    return time.time_ns() // 1_000_000


def clock_ms(value):
    require(type(value) is int and 0 <= value <= 2**63 - 30001)
    return value


def instant(value):
    clock_ms(value)
    require(value <= 8_640_000_000_000_000)
    return value


def guard(config):
    try:
        Policy(config, create=False).check_stop()
    except Stopped:
        raise Denied('Workflow queue is stopped; pending work cannot be admitted') from None


def payload(value):
    require(isinstance(value, dict) and set(value) == {
        'version', 'kind', 'store', 'scope', 'project', 'objective', 'model', 'files', 'options'})
    require(type(value['version']) is int and value['version'] == 1 and value['kind'] == 'inspection')
    require(hex_id(value['store'], 32) and hex_id(value['scope'], 64))
    require(isinstance(value['project'], str) and label(value['project'], project=True) == value['project'])
    require(isinstance(value['objective'], str) and 0 < len(value['objective'].strip()) <= 12000
            and clean(value['objective']) == value['objective'])
    require(isinstance(value['model'], str) and 0 < len(value['model']) <= 200
            and clean(value['model']) == value['model'] and not any(ord(c) < 32 for c in value['model']))
    paths(value['files'])
    require(isinstance(value['options'], dict) and set(value['options']) == set(InferenceOptions.__dataclass_fields__))
    InferenceOptions.from_config(value['options'])
    return value


def encode(value):
    payload(value)
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    require(len(text.encode()) <= MAX_BYTES)
    return text


def load(db, job):
    require(hex_id(job))
    row = db.execute('SELECT id,request_key,conversation,CASE WHEN length(cast(payload AS BLOB))<=? '
        'THEN payload END AS payload,sha256,state,owner,token_sha256,expires_ms,task,created_ms,updated_ms '
        'FROM workflow_queue WHERE id=?', (MAX_BYTES, job)).fetchone()
    if row is None:
        raise KeyError('Queued workflow not found')
    require(hex_id(row['request_key'], 64) and row['state'] in STATES)
    require(isinstance(row['conversation'], str) and 0 < len(row['conversation']) <= 128)
    require(isinstance(row['payload'], str) and hex_id(row['sha256'], 64)
            and hashlib.sha256(row['payload'].encode()).hexdigest() == row['sha256'])
    clock_ms(row['created_ms'])
    clock_ms(row['updated_ms'])
    if row['state'] == 'leased':
        require(row['task'] is None and hex_id(row['owner']) and hex_id(row['token_sha256'], 64))
        clock_ms(row['expires_ms'])
    else:
        require(row['owner'] is None and row['token_sha256'] is None and row['expires_ms'] is None)
        require((row['task'] is None or hex_id(row['task'])) if row['state'] == 'admitted' else row['task'] is None)
    try:
        value = json.loads(row['payload'])
        payload(value)
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ValueError('Unsupported queued workflow payload') from None
    return {**dict(row), 'data': value}


def public(row):
    return {key: row[key] for key in ('id', 'conversation', 'state', 'task', 'created_ms', 'updated_ms')}


@dataclass(frozen=True)
class Claim:
    job: str
    owner: str
    token: str = field(repr=False)


def match(db, claim, timestamp):
    require(isinstance(claim, Claim) and hex_id(claim.job) and hex_id(claim.owner) and hex_id(claim.token, 64))
    clock_ms(timestamp)
    row = load(db, claim.job)
    require(row['state'] == 'leased' and row['task'] is None and row['owner'] == claim.owner
            and row['expires_ms'] > timestamp
            and hmac.compare_digest(row['token_sha256'], hashlib.sha256(claim.token.encode()).hexdigest()))
    return row


def validate_admission(db, claim, spec, conversation):
    row = match(db, claim, now_ms())
    expected = {'version': 1, 'kind': 'inspection', 'store': spec['store'], 'scope': spec['scope'],
                'project': spec['project'], 'objective': spec['objective'], 'model': spec['model'],
                'files': [item['path'] for item in spec['files']], 'options': spec['options']}
    require(row['conversation'] == conversation and row['data'] == expected and spec['attempt'] == 1)


def attach(db, claim, task):
    match(db, claim, now_ms())
    cursor = db.execute("UPDATE workflow_queue SET state='admitted',task=?,owner=NULL,token_sha256=NULL,"
                        'expires_ms=NULL,updated_ms=? WHERE id=? AND task IS NULL', (task, now_ms(), claim.job))
    require(cursor.rowcount == 1)


class WorkQueue:
    def __init__(self, store, config, owner, *, clock=None):
        require(hex_id(owner))
        self.store, self.config, self.owner = store, config, owner
        self.clock = clock or now_ms

    def enqueue(self, request_key, conversation, objective, model, project, files, settings):
        require(hex_id(request_key, 64))
        require(isinstance(conversation, str) and 0 < len(conversation) <= 128)
        text = self.prepare(objective, model, project, files, settings)
        stamp = clock_ms(self.clock())
        with self.store.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            return insert(db, request_key, conversation, text, stamp)

    def prepare(self, objective, model, project, files, settings):
        guard(self.config)
        base = Policy(self.config, create=False)
        require(isinstance(project, str) and label(project, project=True) == project)
        base.no_links(base.root / project)
        root = base.path(project)
        config = copy.deepcopy(self.config)
        config['paths']['workspace'] = str(root)
        require(isinstance(settings, dict) and not set(settings) - set(InferenceOptions.__dataclass_fields__))
        observe(Policy(config, create=False), files)
        value = {'version': 1, 'kind': 'inspection', 'store': self.store.identity, 'scope': scope_key(root),
                 'project': project, 'objective': clean(objective), 'model': model, 'files': list(files),
                 'options': asdict(InferenceOptions.from_config({**config['model'], **settings}))}
        return encode(value)

    def claim(self, *, seconds=15, scheduled_only=False, automatic_only=False):
        require(type(seconds) is int and 1 <= seconds <= 30)
        require(type(scheduled_only) is bool)
        require(type(automatic_only) is bool and not (scheduled_only and automatic_only))
        guard(self.config)
        stamp = clock_ms(self.clock())
        with self.store.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            selected = 'AND id IN (SELECT job FROM schedule_runs)' if scheduled_only else ''
            if automatic_only:
                selected = 'AND id IN (SELECT job FROM schedule_runs UNION SELECT job FROM directory_runs)'
            candidates = list(db.execute("SELECT id FROM workflow_queue WHERE task IS NULL AND "
                f"(state='queued' OR (state='leased' AND expires_ms<=?)) {selected} ORDER BY created_ms,rowid LIMIT ?", (stamp, MAX_SCAN)))
            for candidate in candidates:
                try:
                    row = load(db, candidate['id'])
                    require(row['data']['store'] == self.store.identity)
                except (ValueError, TypeError):
                    db.execute("UPDATE workflow_queue SET state='blocked',owner=NULL,token_sha256=NULL,expires_ms=NULL,"
                               'updated_ms=? WHERE id=? AND task IS NULL', (stamp, candidate['id']))
                    continue
                token = secrets.token_hex(32)
                db.execute("UPDATE workflow_queue SET state='leased',owner=?,token_sha256=?,expires_ms=?,updated_ms=? WHERE id=?",
                    (self.owner, hashlib.sha256(token.encode()).hexdigest(), stamp + seconds * 1000, stamp, row['id']))
                return Claim(row['id'], self.owner, token)
        return None

    def request(self, claim):
        require(isinstance(claim, Claim) and claim.owner == self.owner)
        guard(self.config)
        with self.store.connection() as db:
            row = match(db, claim, clock_ms(self.clock()))
            require(row['data']['store'] == self.store.identity)
            return {'conversation': row['conversation'], **row['data']}

    def release(self, claim, *, retry=False):
        require(isinstance(claim, Claim) and claim.owner == self.owner and type(retry) is bool)
        stamp = clock_ms(self.clock())
        with self.store.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            match(db, claim, stamp)
            db.execute('UPDATE workflow_queue SET state=?,owner=NULL,token_sha256=NULL,expires_ms=NULL,updated_ms=? WHERE id=?',
                       ('queued' if retry else 'blocked', stamp, claim.job))

    def cancel(self, job):
        require(hex_id(job))
        with self.store.connection() as db:
            cursor = db.execute("UPDATE workflow_queue SET state='cancelled',owner=NULL,token_sha256=NULL,expires_ms=NULL,"
                "updated_ms=? WHERE id=? AND task IS NULL AND state IN ('queued','leased')", (clock_ms(self.clock()), job))
            return cursor.rowcount == 1

    def summary(self, job):
        with self.store.connection() as db:
            return public(load(db, job))


def insert(db, request_key, conversation, text, stamp):
    """Caller owns the writer transaction; timer advancement can share this commit."""
    require(hex_id(request_key, 64))
    encode(json.loads(text))
    clock_ms(stamp)
    existing = db.execute('SELECT id FROM workflow_queue WHERE request_key=?', (request_key,)).fetchone()
    if existing:
        row = load(db, existing['id'])
        require(row['conversation'] == conversation and row['payload'] == text)
        return public(row)
    count, size = db.execute('SELECT count(*),coalesce(sum(length(cast(payload AS BLOB))),0) FROM workflow_queue').fetchone()
    if count >= MAX_ITEMS or size + len(text.encode()) > MAX_TOTAL_BYTES:
        raise ValueError('Workflow queue storage is full; review retained conversation history')
    if not db.execute('SELECT 1 FROM conversations WHERE id=?', (conversation,)).fetchone():
        raise KeyError('Conversation not found')
    ident = uuid.uuid4().hex
    db.execute("INSERT INTO workflow_queue VALUES (?,?,?,?,?,'queued',NULL,NULL,NULL,NULL,?,?)",
               (ident, request_key, conversation, text, hashlib.sha256(text.encode()).hexdigest(), stamp, stamp))
    return public(load(db, ident))


def task_status(db, queued):
    if not queued['task']:
        return None
    row = db.execute('SELECT conversation,mode,CASE WHEN length(status)<=20 THEN status END AS status '
                     'FROM tasks WHERE id=?', (queued['task'],)).fetchone()
    require(row is not None and row['conversation'] == queued['conversation'] and row['mode'] == 'inspection')
    require(row['status'] in {'running', 'waiting', 'reported', 'planned', 'no_actions', 'blocked',
                              'failed', 'cancelled', 'interrupted'})
    return row['status']
