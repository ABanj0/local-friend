"""Derived memory index contracts. Protocol fixtures do not establish retrieval quality."""
import hashlib
import json
import os
import sqlite3
import struct
import threading
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from local_agent.embeddings import EmbeddingError
from local_agent.safety import Denied
from local_agent.studio import migrations
from local_agent.studio.manager import Manager
from local_agent.studio.memory_index import identity
from local_agent.studio.store import Store
from tests import studio_support as fixtures
from tests.memory_index_support import MemoryIndexFixture
from tests.support import WorkspaceTest


class MemoryIndexTests(MemoryIndexFixture, WorkspaceTest):
    def test_persisted_exact_vectors_hashes_scope_and_restart(self):
        result = self.build()
        self.assertEqual(result['indexed'], 1)
        self.assertFalse(result['automatic_retrieval'])
        with self.manager.store.connection() as db:
            row = db.execute('SELECT * FROM memory_vectors').fetchone()
            self.assertEqual(row['source_sha256'], self.note['sha256'])
            self.assertEqual(struct.unpack('<2f', row['vector']), (1., 0.))
            self.assertEqual(row['vector_sha256'], hashlib.sha256(row['vector']).hexdigest())
        self.assertEqual(self.index.status('.')['state'], 'locally_current')
        self.assertEqual(self.index.status('.')['model_check'], 'not_checked')
        restarted = Manager(self.config)
        self.addCleanup(restarted.close)
        self.assertEqual(restarted.memory_index.search('.', 'Which build option?')[0]['id'], self.note['id'])
        before = len(self.calls)
        with self.assertRaisesRegex(ValueError, 'not indexed'):
            restarted.memory_index.search('other', 'Which build option?')
        self.assertEqual(len(self.calls), before)

    def test_confirmation_invalid_inputs_stop_and_active_task_precede_inference(self):
        for confirmed in (False, 'true', 1):
            with self.assertRaises(Denied):
                self.index.reindex('.', 'fixture', confirmed=confirmed)
        for model in ('', 'https://remote.invalid?x=1', True):
            with self.assertRaises(ValueError):
                self.index.reindex('.', model, confirmed=True)
        for query in ('', True, 'x' * 501):
            with self.assertRaises(ValueError):
                self.index.search('.', query)
        self.manager.running['active'] = {}
        try:
            with self.assertRaises(ValueError):
                self.build()
        finally:
            self.manager.running.clear()
        (self.policy.state / 'STOP').touch()
        with self.assertRaises(Denied):
            self.build()
        self.assertEqual(self.calls, [])

    def test_failed_reindex_preserves_old_generation_and_vectors(self):
        self.build()
        with self.manager.store.connection() as db:
            before = [tuple(r) for r in db.execute('SELECT * FROM memory_indexes')]
            vectors = [tuple(r) for r in db.execute('SELECT * FROM memory_vectors')]
        self.on_embed = lambda *_: (_ for _ in ()).throw(EmbeddingError('private failure'))
        with self.assertRaisesRegex(ValueError, 'existing index was preserved'):
            self.build()
        with self.manager.store.connection() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM memory_indexes')], before)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM memory_vectors')], vectors)
        self.assertFalse(self.index.busy)

    def test_new_note_during_embedding_refuses_publication(self):
        self.on_embed = lambda *_: self.manager.memory.remember('.', self.chat, 'Added during inference')
        with self.assertRaises(Denied):
            self.build()
        self.assertEqual(self.counts(), (0, 0))

    def test_sql_failure_after_index_replacement_rolls_back_entire_publication(self):
        self.build()
        with self.manager.store.connection() as db:
            before = [tuple(r) for r in db.execute('SELECT * FROM memory_indexes')]
            vectors = [tuple(r) for r in db.execute('SELECT * FROM memory_vectors')]
            db.execute("CREATE TRIGGER refuse_vector BEFORE INSERT ON memory_vectors BEGIN "
                       "SELECT RAISE(ABORT,'Injected publication fault'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.build()
        with self.manager.store.connection() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM memory_indexes')], before)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM memory_vectors')], vectors)
        self.assertFalse(self.index.busy)

    def test_forget_and_source_chat_deletion_cascade_vectors(self):
        self.build()
        self.manager.memory.forget('.', self.note['id'], confirmed=True)
        self.assertEqual(self.counts(), (1, 0))
        self.assertEqual(self.index.status('.')['state'], 'reindex_required')
        self.note = self.manager.memory.remember('.', self.chat, 'Another saved note')
        self.build()
        self.manager.store.delete_conversation(self.chat)
        self.assertEqual(self.counts(), (1, 0))

    def test_model_change_and_note_change_require_reindex_before_query_text(self):
        self.build()
        self.calls.clear()
        self.ident['digest'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'model changed'):
            self.index.search('.', 'private query text')
        self.assertFalse(any(isinstance(c, tuple) for c in self.calls))
        self.build()
        self.manager.memory.remember('.', self.chat, 'A new note')
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, 'Saved notes changed'):
            self.index.search('.', 'question')
        self.assertEqual(self.calls, [])

    def test_delete_or_cancel_during_query_cannot_return_removed_note(self):
        for cancel in (False, True):
            if cancel:
                self.note = self.manager.memory.remember('.', self.chat, 'Replacement source')
            self.on_embed = None
            self.build()

            def intervene(*_, cancel=cancel):
                if cancel:
                    self.manager.close()
                else:
                    self.manager.memory.forget('.', self.note['id'], confirmed=True)

            self.on_embed = intervene
            with self.subTest(cancel=cancel), self.assertRaises(Denied):
                self.index.search('.', 'question')
            self.assertFalse(self.index.busy)

    def test_embedding_never_holds_manager_lock_and_duplicate_or_task_start_is_refused(self):
        entered, release = threading.Event(), threading.Event()
        errors = []

        def block(*_):
            entered.set()
            if not release.wait(3):
                raise AssertionError('Test did not release embedding fixture')

        def run():
            try:
                self.build()
            except (Denied, ValueError, EmbeddingError, AssertionError) as exc:
                errors.append(exc)

        self.on_embed = block
        thread = threading.Thread(target=run)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.manager.lock.acquire(timeout=.5))
            self.manager.lock.release()
            with self.assertRaisesRegex(ValueError, 'already active'):
                self.build()
            with self.assertRaisesRegex(ValueError, 'embedding operation'):
                self.manager.start(self.chat, 'question', 'chat', 'fixture')
            self.manager.close()
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Denied)
        self.assertEqual(self.counts(), (0, 0))

    def test_host_close_interrupts_real_http_and_cannot_publish_index(self):
        entered, release = threading.Event(), threading.Event()
        errors = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', '1000')
                self.end_headers()
                entered.set()
                release.wait(3)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        self.client_patch.stop()
        self.config['model']['url'] = f'http://127.0.0.1:{server.server_port}'

        def index():
            try:
                self.build()
            except (ValueError, Denied) as exc:
                errors.append(exc)

        thread = threading.Thread(target=index)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.manager.close()
            thread.join(1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors), 1)
            self.assertFalse(self.index.busy)
            self.assertEqual(self.counts(), (0, 0))
            self.assertTrue(serving.is_alive(), 'Closing a request must not stop its listener')
        finally:
            release.set()
            thread.join(3)
            server.shutdown()
            server.server_close()
            serving.join(2)

    def test_corrupt_vector_or_metadata_is_rejected_without_query_inference(self):
        for corruption in ('length', 'hash', 'nan', 'identity'):
            self.build()
            with self.manager.store.connection() as db:
                if corruption == 'length':
                    db.execute("UPDATE memory_vectors SET vector=X'01'")
                elif corruption == 'hash':
                    db.execute('UPDATE memory_vectors SET vector_sha256=?', ('0' * 64,))
                elif corruption == 'nan':
                    raw = struct.pack('<2f', float('nan'), 1.)
                    db.execute('UPDATE memory_vectors SET vector=?,vector_sha256=?', (raw, hashlib.sha256(raw).hexdigest()))
                else:
                    db.execute("UPDATE memory_indexes SET identity='{}'")
            self.calls.clear()
            with self.subTest(corruption=corruption), self.assertRaises((ValueError, EmbeddingError)):
                self.index.search('.', 'question')
            self.assertEqual(self.calls, [])

    def test_exact_credentials_and_tampered_note_hash_do_not_reach_embedding(self):
        with self.assertRaises(Denied):
            self.index.reindex('.', 'fixture', confirmed=True, forbidden=('lavender',))
        self.assertEqual(self.calls, [])
        with self.manager.store.connection() as db:
            db.execute("UPDATE memories SET text='changed' WHERE id=?", (self.note['id'],))
        with self.assertRaisesRegex(ValueError, 'hash changed'):
            self.build()
        self.assertEqual(self.calls, [])

    def test_identity_validation_rejects_invalid_dimension_and_format(self):
        for key, value in (('dimensions', True), ('dimensions', 0), ('dimensions', 4097),
                           ('digest', 'bad'), ('query_format', 'other'), ('model', 'http://x?y')):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                identity({**self.ident, key: value})

    def test_v8_upgrade_failure_rolls_back_and_success_preserves_identity_and_notes(self):
        path = self.policy.state / 'v8.sqlite3'
        required = {k: v for k, v in migrations.REQUIRED.items() if k not in {'memory_indexes', 'memory_vectors', 'memory_file_sources', 'memory_file_chunks'}}
        with (patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:8]),
              patch.object(migrations, 'SCHEMA_VERSION', 8), patch.object(migrations, 'REQUIRED', required)):
            old = Store(path)
            chat = old.conversation('Preserved v8')
            old.message(chat, 'user', 'Saved transcript')
            with old.connection() as db:
                db.execute("INSERT INTO memory_domains(scope) VALUES ('scope-fixture')")
                db.execute("INSERT INTO memories VALUES (?,?,?,?,?,?,?)", (
                    'f' * 32, 'scope-fixture', chat, None, 'Retained note',
                    hashlib.sha256(b'Retained note').hexdigest(), 1.))

        def fail(db):
            migrations.memory_vectors(db)
            raise RuntimeError('Injected migration failure')

        with (patch.object(migrations, 'MIGRATIONS', (*migrations.MIGRATIONS[:8], ('memory_vectors', fail))),
              self.assertRaises(RuntimeError)):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 8)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_schema WHERE name='memory_indexes'").fetchone())
        upgraded = Store(path)
        self.assertEqual(upgraded.identity, old.identity)
        self.assertEqual(upgraded.messages(chat)[0]['content'], 'Saved transcript')
        with upgraded.connection() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], migrations.SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT text FROM memories').fetchone()[0], 'Retained note')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])


@unittest.skipUnless(fixtures.HAS_API, 'FastAPI optional dependency missing')
class MemoryIndexAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_auth_origin_strict_confirmation_scope_and_actual_index_routes(self):
        manager = self.client.app.state.manager
        chat = manager.store.conversation()
        manager.memory.remember('.', chat, 'Atlas requires lavender flags.')
        for route in ('/memory/index', '/memory/hybrid?query=flags'):
            self.assertEqual(self.client.get(route).status_code, 401)
            self.assertEqual(self.client.get(route, headers={**self.headers, 'Origin': 'https://evil.invalid'}).status_code, 403)
        self.assertEqual(self.client.post('/memory/index', json={}).status_code, 401)
        body = {'model': 'fixture', 'confirmed': True}
        self.assertEqual(self.client.post('/memory/index', headers=self.headers,
                                          json={**body, 'confirmed': 'true'}).status_code, 422)
        self.assertEqual(self.client.post('/memory/index', headers=self.headers,
                                          json={**body, 'confirmed': False}).status_code, 403)
        self.assertEqual(self.client.post('/memory/index', headers=self.headers,
                                          json={**body, 'project': '../'}).status_code, 403)
        self.assertEqual(self.client.get('/memory/index', headers=self.headers).json()['state'], 'not_indexed')
        self.assertEqual(self.client.get('/memory/hybrid?query=flags', headers=self.headers).status_code, 400)

        class Protocol:
            def __init__(self, config):
                self.model = config['name']

            def identity(self):
                return {'model': self.model, 'digest': 'a' * 64, 'server_version': '0.40.7',
                        'dimensions': 2, 'query_format': 'project-note-instruct-v1'}

            def embed(self, texts, *, query=False):
                return self.identity(), [[1., 0.] for _ in texts]

        with patch('local_agent.studio.memory_index.Embeddings', Protocol):
            response = self.client.post('/memory/index', headers=self.headers, json=body)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['indexed'], 1)
            self.assertEqual(self.client.get('/memory/index', headers=self.headers).json()['state'], 'locally_current')
            response = self.client.get('/memory/hybrid?query=flags', headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()[0]['conversation'], chat)
            self.assertEqual(self.client.get('/memory/hybrid?query=' + 'x' * 64, headers=self.headers).status_code, 403)
        # Direct note-source lookup and keyword API remain unchanged.
        self.assertEqual(self.client.get('/memory?query=flags', headers=self.headers).json()[0]['conversation'], chat)


@unittest.skipUnless(os.environ.get('LIVE_EMBEDDINGS') == '1', 'Actual embedding index acceptance is opt-in')
class LiveMemoryIndexTests(WorkspaceTest):
    def test_real_model_restart_paraphrase_citation_and_forget(self):
        from local_agent.benchmark import ensure_idle
        from local_agent.config import load
        ensure_idle(load())
        manager = Manager(self.config)
        self.addCleanup(manager.close)
        chat = manager.store.conversation()
        note = manager.memory.remember('.', chat, 'Atlas compiler requires the lavender optimization flag for release builds.')
        (self.policy.root / 'other').mkdir()
        other_chat = manager.store.conversation()
        other = manager.memory.remember('other', other_chat, note['text'])
        result = manager.memory_index.reindex('.', 'qwen3-embedding:0.6b', confirmed=True)
        self.assertEqual(result['indexed'], 1)
        restarted = Manager(self.config)
        self.addCleanup(restarted.close)
        rows = restarted.memory_index.search('.', 'Which release compilation setting is mandatory?')
        self.assertEqual([r['id'] for r in rows], [note['id']])
        self.assertEqual(rows[0]['conversation'], chat)
        self.assertNotIn(other['id'], [r['id'] for r in rows])
        restarted.memory.forget('.', note['id'], confirmed=True)
        with restarted.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_vectors').fetchone()[0], 0)
        with self.assertRaises(ValueError):
            restarted.memory_index.search('.', 'Which setting?')
        print('Actual embedding index:', json.dumps({'indexed': result['indexed'], 'identity': result['identity'],
              'restart_source_preserved': True, 'outside_results': 0, 'forgotten_vectors': 0}))
