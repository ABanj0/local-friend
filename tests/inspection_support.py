"""Non-discoverable fixtures for supported inspection checkpoints and actual workers."""
import copy
import hashlib
import json
import struct
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from local_agent.agent import EXECUTE_PROMPT, SYSTEM, clean
from local_agent.coding import Coding
from local_agent.inference import InferenceOptions
from local_agent.safety import Policy
from local_agent.studio import inspection
from local_agent.studio.journal import scope_key
from local_agent.studio.manager import Manager

from .ollama_fixture import serve_metadata


def spec_for(config, store, chat, files=('a.py', 'b.py')):
    policy = Policy(config, create=False)
    with store.connection() as db:
        epoch = db.execute('SELECT memory_epoch FROM conversations WHERE id=?', (chat,)).fetchone()[0]
    return {'version': 1, 'runtime': inspection.runtime(policy), 'store': store.identity,
        'scope': scope_key(policy.root), 'project': '.', 'epoch': epoch, 'objective': 'Inspect these files',
        'files': inspection.observe(policy, list(files))[0], 'model': config['model']['name'],
        'identity': {'digest': 'd' * 64, 'server_version': '0.40.7'},
        'options': asdict(InferenceOptions.from_config(config['model'])),
        'max_steps': config['model']['max_steps'], 'attempt': 1, 'prior_reads': 0}


def agent_for(config, spec, files=('a.py',)):
    messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': inspection.prompt(spec)},
        {'role': 'assistant', 'content': '{"steps":["Read the selected files","Report observations"]}'},
        {'role': 'user', 'content': EXECUTE_PROMPT}]
    for path in files:
        messages += [{'role': 'assistant', 'tool_calls': [{'function': {'name': 'read_file', 'arguments': {'path': path}}}]},
            {'role': 'tool', 'tool_name': 'read_file', 'content': json.dumps(
                {'ok': True, 'untrusted_data': clean(Coding(Policy(config, create=False)).read(path))})}]
    return {'version': 1, 'messages': messages, 'evidence': [{'tool': 'read_file', 'ok': True, 'exit_code': None} for _ in files],
            'failures': 0, 'empty_responses': 0, 'next_step': len(files)}


def seed_closed_checkpoint(config, store, chat):
    path = Policy(config, create=False).root / 'copy-inspection.py'
    path.write_text('# PRIVATE-CHECKPOINT-FIXTURE\n', encoding='utf-8')
    spec = spec_for(config, store, chat, files=[path.name])
    task = store.task(chat, 'inspection', spec['model'], profile='coding', project='.', scope_key=spec['scope'],
                      inspection={'spec': spec, 'agent': None})
    store.complete(task, {'status': 'cancelled', 'report': 'Closed private checkpoint fixture'})
    from local_agent.studio.work_queue import WorkQueue
    queue = WorkQueue(store, config, 'f' * 32)
    item = queue.enqueue('f' * 64, chat, spec['objective'], spec['model'], '.', [path.name], spec['options'])
    queue.cancel(item['id'])
    with store.connection() as db:
        row = db.execute('SELECT payload,sha256,created_ms FROM workflow_queue WHERE id=?', (item['id'],)).fetchone()
        db.execute('INSERT INTO interval_schedules VALUES (?,?,?,?,?,60000,?,?,?, ?,?)',
                   ('f' * 32, chat, row[0], row[1], 0, row[2] + 60000, 'skip', 'UTC', 'disabled', row[2]))
        db.execute('INSERT INTO schedule_runs VALUES (?,?,?)', (item['id'], 'f' * 32, row[2]))
    from local_agent.studio.watches import trigger
    watch, fingerprint = 'e' * 32, 'b' * 64
    watched = queue.enqueue(trigger(watch, 1, fingerprint), chat, spec['objective'], spec['model'], '.', [path.name], spec['options'])
    queue.cancel(watched['id'])
    with store.connection() as db:
        row = db.execute('SELECT payload,sha256,created_ms FROM workflow_queue WHERE id=?', (watched['id'],)).fetchone()
        db.execute('INSERT INTO directory_watches VALUES (?,?,?,?,?,?,0,1000,?,NULL,NULL,?,1,0,?,?)',
                   (watch, chat, row[0], row[1], '.', scope_key(Policy(config, create=False).root),
                    fingerprint, row[2], 'disabled', row[2]))
        db.execute('INSERT INTO directory_runs VALUES (?,?,1,?)', (watched['id'], watch, fingerprint))
        # Backup/restore preservation must include actual derived-vector rows as well.
        note = db.execute('SELECT id,scope,sha256,text FROM memories WHERE conversation=? LIMIT 1', (chat,)).fetchone()
        scope = note['scope']
        rows = db.execute('SELECT id,sha256 FROM memories WHERE scope=? ORDER BY id', (scope,)).fetchall()
        manifest = hashlib.sha256(json.dumps([tuple(r) for r in rows], separators=(',', ':')).encode()).hexdigest()
        epoch = db.execute('SELECT epoch FROM memory_domains WHERE scope=?', (scope,)).fetchone()[0]
        identity = {'model': 'fixture', 'digest': 'a' * 64, 'server_version': '0.40.7',
                    'dimensions': 2, 'query_format': 'project-note-instruct-v1'}
        db.execute('INSERT INTO memory_indexes VALUES (?,?,?,?,?,?)',
                   (scope, json.dumps(identity, sort_keys=True), manifest, epoch, 'c' * 32, 1.))
        vector = struct.pack('<2f', 1., 0.)
        db.execute('INSERT INTO memory_vectors VALUES (?,?,?,?,?)',
                   (scope, note['id'], note['sha256'], vector, hashlib.sha256(vector).hexdigest()))
        from local_agent.review import fingerprint
        from local_agent.studio.memory_sources import VIEW, digest
        source_path = Policy(config, create=False).root / 'memory-source.txt'
        source_path.write_text(note['text'], encoding='utf-8', newline='')
        version = fingerprint(source_path, 64000)
        db.execute('INSERT INTO memory_file_sources VALUES (?,?,?,?,?,?,?,?,?,?,?)', (
            'd' * 32, scope, chat, source_path.name, version[-1], digest(version[1:]), VIEW,
            'b' * 32, 'current', '', 1.))
        db.execute('INSERT INTO memory_file_chunks VALUES (?,?,?,?,?,?,?,?)', (
            scope, note['id'], 'd' * 32, 0, 0, len(note['text']), 1, note['text'].count('\n') + 1))
    return task


class InspectionModelFixture:
    def setUp(self):
        super().setUp()
        self.requests = []
        self.gate = threading.Event()
        self.entered = threading.Event()
        self.gate.set()
        self.model_tool = 'read_file'
        self.model_digest = 'a' * 64
        self.finish_after = 2
        self.metadata_gate = threading.Event()
        self.metadata_gate.set()
        self.metadata_entered = threading.Event()
        owner = self

        class Protocol(BaseHTTPRequestHandler):
            def handle(self):
                try:
                    super().handle()
                except ConnectionError:
                    pass  # Owned preflight cancellation can reset even before the request line.

            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == '/api/tags':
                    owner.metadata_entered.set()
                    owner.metadata_gate.wait(10)
                try:
                    if not serve_metadata(self, name=owner.config['model']['name'], digest=owner.model_digest):
                        self.send_error(404)
                except ConnectionError:
                    pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if serve_metadata(self, body, name=owner.config['model']['name'], digest=owner.model_digest):
                    return
                owner.requests.append(copy.deepcopy(body))
                tools = [message for message in body['messages'] if message['role'] == 'tool']
                if body.get('format'):
                    message = {'content': '{"steps":["Read a.py","Read b.py","Report observations"]}'}
                elif len(tools) >= owner.finish_after:
                    message = {'content': 'Inspected both selected files. No changes or commands were run.'}
                else:
                    if len(tools) == 1:
                        owner.entered.set()
                        owner.gate.wait(30)
                    name = owner.model_tool
                    arguments = {'path': 'a.py' if not tools else 'b.py'}
                    if name == 'write_file':
                        arguments['text'] = 'MUTATION-MUST-NOT-EXIST'
                    elif name == 'command':
                        arguments = {'name': 'test'}
                    elif name == 'outside':
                        name, arguments = 'read_file', {'path': 'outside.py'}
                    message = {'thinking': 'PRIVATE-THINKING-CANARY',
                               'tool_calls': [{'function': {'name': name, 'arguments': arguments}}]}
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'message': {'role': 'assistant', **message}, 'done': True,
                        'done_reason': 'stop', 'eval_count': 10, 'eval_duration': 100000000}).encode())
                except ConnectionError:
                    pass  # Intentional owned-worker termination closes the pending model request.

        self.model_server = ThreadingHTTPServer(('127.0.0.1', 0), Protocol)
        threading.Thread(target=self.model_server.serve_forever, daemon=True).start()
        self.addCleanup(self.model_server.server_close)
        self.addCleanup(self.model_server.shutdown)
        self.addCleanup(self.gate.set)
        self.addCleanup(self.metadata_gate.set)
        self.config['model']['url'] = f'http://127.0.0.1:{self.model_server.server_port}'
        (self.policy.root / 'a.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
        (self.policy.root / 'b.py').write_text('from a import add\nassert add(2, 3) == 5\n', encoding='utf-8')

    def wait_until(self, predicate):
        import time
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.02)
        self.fail('Actual inspection worker did not reach the expected boundary')


class InspectionProcessFixture(InspectionModelFixture):
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.store = self.manager.store
        self.chat = self.store.conversation('Inspection fixture')

    def start_inspection(self):
        return inspection.start(self.manager, self.chat, 'Explain these files',
            self.config['model']['name'], '.', ['a.py', 'b.py'], {})
