"""Confirmed generation switches preserve current state and freshly captured rollback."""
import hashlib
import json
import multiprocessing
import os
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest import skipUnless
from unittest.mock import patch

from local_agent.safety import Denied
from local_agent.studio import backups, restore_activation, restores
from local_agent.studio.manager import Manager
from local_agent.studio.restore_gate import RestoreGate
from local_agent.studio.state_owner import StateOwner, read_pointer

from . import studio_support as fixtures
from .support import WorkspaceTest


def activation_crash(config, draft, after):
    owner = StateOwner(config)
    manager = Manager(config)
    publish = restore_activation.atomic_write

    def crash(*args, **kwargs):
        if after:
            publish(*args, **kwargs)
        os._exit(27)

    with patch.object(restore_activation, 'atomic_write', crash):
        restore_activation.activate(manager, owner, draft['id'], draft['database_sha256'],
                                    confirmed=True, require_restart=lambda: None)


class ActivationTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.owner = StateOwner(self.config)
        self.addCleanup(self.owner.close)
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.original = self.manager.store
        self.chat = self.original.conversation('Saved before backup')
        self.original.message(self.chat, 'user', 'PRIVATE-CURRENT-CONTENT')
        item = backups.create(self.manager, confirmed=True)
        self.newer = self.original.conversation('Newer current data')
        self.draft = restores.prepare(self.manager, item['id'], item['sha256'], confirmed=True)
        self.latest = self.original.conversation('Changed after preparation')
        self.gate = RestoreGate()
        self.gate.enter()
        self.target = self.policy.state / 'restore-staging' / self.draft['id'] / 'studio.sqlite3'
        self.marker = self.target.with_name('ready.json')

    def activate(self, **kwargs):
        with self.gate.freeze():
            return restore_activation.activate(self.manager, self.owner, self.draft['id'],
                self.draft['database_sha256'], confirmed=True, require_restart=self.gate.require_restart, **kwargs)

    def restart(self):
        self.manager.close(shutdown=True)
        self.owner.close()
        self.owner = StateOwner(self.config)
        self.addCleanup(self.owner.close)
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.gate = RestoreGate()
        self.gate.enter()

    def test_activation_retains_original_and_fresh_rollback_then_restart_selects_generation(self):
        result = self.activate()
        self.assertTrue(result['restart_required'])
        self.assertTrue(result['original_retained'])
        self.assertTrue(self.gate.pending)
        self.assertTrue(self.manager.restore_pending.is_set())
        self.assertFalse(self.manager.diagnostics()['ready'])
        self.assertEqual(len(self.original.conversations()), 3)
        self.assertEqual(self.manager.store.path, self.original.path)
        self.assertNotEqual(result['rollback'], self.draft['rollback'])
        rollback = self.policy.state / 'backups' / (result['rollback'] + '.sqlite3')
        self.assertEqual(hashlib.sha256(rollback.read_bytes()).hexdigest(), result['rollback_sha256'])
        with closing(sqlite3.connect(rollback)) as db:
            self.assertEqual({r[0] for r in db.execute('SELECT id FROM conversations')}, {self.chat, self.newer, self.latest})
        with self.assertRaisesRegex(ValueError, 'restart'):
            self.manager.start(self.chat, 'Must not run before restart', 'agent', 'fixture')
        with self.assertRaises(ValueError):
            backups.create(self.manager, confirmed=True)
        self.restart()
        self.assertEqual(self.manager.store.path, self.target)
        self.assertEqual(self.manager.store.identity, self.draft['store_id'])
        self.assertEqual([c['id'] for c in self.manager.store.conversations()], [self.chat])
        self.assertEqual(self.manager.store.messages(self.chat)[0]['content'], 'PRIVATE-CURRENT-CONTENT')
        self.assertFalse(self.manager.running)
        self.assertFalse(self.manager.restore_pending.is_set())
        self.assertEqual(len(self.original.conversations()), 3)
        self.assertTrue(backups.create(self.manager, confirmed=True)['sha256'])

    def test_rollback_uses_same_confirmed_flow_in_another_fresh_generation(self):
        result = self.activate()
        self.restart()
        inspected = backups.inspect(self.manager, result['rollback'])
        self.draft = restores.prepare(self.manager, inspected['id'], inspected['sha256'], confirmed=True)
        second = self.activate()
        self.assertNotEqual(second['generation'], result['generation'])
        self.restart()
        self.assertEqual({c['id'] for c in self.manager.store.conversations()}, {self.chat, self.newer, self.latest})
        self.assertEqual(len(self.original.conversations()), 3)

    def test_denial_owned_cleanup_shutdown_stop_and_closed_owner_never_publish(self):
        for confirmation in (False, None, 1, 'true'):
            with self.assertRaises(Denied):
                restore_activation.activate(self.manager, self.owner, self.draft['id'], self.draft['database_sha256'],
                    confirmed=confirmation, require_restart=self.gate.require_restart)
        for state in ({'done': False}, {'done': True}, {'done': True, 'persist_error': 'private'}):
            self.manager.running['owner'] = state
            try:
                with self.assertRaises(ValueError):
                    self.activate()
            finally:
                self.manager.running.clear()
        self.manager.shutdown_requested.set()
        with self.assertRaises(ValueError):
            self.activate()
        self.manager.shutdown_requested.clear()
        stop = self.policy.state / 'STOP'
        stop.touch()
        with self.assertRaises(Denied):
            self.activate()
        stop.unlink()
        self.owner.close()
        with self.assertRaises(Denied):
            self.activate()
        self.assertIsNone(read_pointer(self.config))
        self.assertFalse(self.manager.restore_pending.is_set())

    def test_strict_metadata_changed_hash_missing_or_linked_candidates_fail_before_intent(self):
        original = self.marker.read_bytes()
        variants = [{**self.draft, 'activated': True}, {**self.draft, 'bytes': True},
                    {**self.draft, 'extra': 'grant authority'}, {**self.draft, 'generation': '../escape'},
                    {**self.draft, 'schema_version': 99}]
        for data in variants:
            self.marker.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                self.activate()
        self.marker.write_bytes(original)
        self.draft['database_sha256'] = 'f' * 64
        with self.assertRaises((ValueError, Denied)):
            self.activate()
        self.draft = json.loads(original)
        alias = self.policy.state / 'alias.sqlite3'
        os.link(self.target, alias)
        with self.assertRaises(Denied):
            self.activate()
        alias.unlink()
        self.marker.unlink()
        with self.assertRaises(ValueError):
            self.activate()
        self.assertIsNone(read_pointer(self.config))
        self.assertFalse(self.manager.restore_pending.is_set())

    def test_hostile_schema_is_rechecked_even_if_manifest_hash_is_forged(self):
        with closing(sqlite3.connect(self.target)) as db, db:
            db.execute('CREATE TRIGGER hostile AFTER UPDATE ON metadata BEGIN DELETE FROM conversations; END')
        self.draft['database_sha256'] = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.marker.write_text(json.dumps(self.draft))
        with self.assertRaisesRegex(ValueError, 'unsupported schema'):
            self.activate()
        self.assertIsNone(read_pointer(self.config))
        self.assertEqual(len(self.original.conversations()), 3)

    def test_changed_candidate_during_fresh_rollback_prevents_publication(self):
        snapshot = backups.create

        def changed(*args, **kwargs):
            result = snapshot(*args, **kwargs)
            with self.target.open('ab') as stream:
                stream.write(b'CHANGED')
            return result

        with patch.object(backups, 'create', changed), self.assertRaises(Denied):
            self.activate()
        self.assertIsNone(read_pointer(self.config))
        self.assertFalse(self.manager.restore_pending.is_set())
        self.assertEqual(len(self.original.conversations()), 3)

    def test_publication_failure_before_or_after_effect_requires_restart_and_never_rolls_back_blindly(self):
        with patch.object(restore_activation, 'atomic_write', side_effect=OSError('Publish failed')), self.assertRaises(OSError):
            self.activate()
        self.assertTrue(self.manager.restore_pending.is_set())
        self.assertTrue(self.gate.pending)
        self.assertIsNone(read_pointer(self.config))
        self.restart()
        self.assertEqual(len(self.manager.store.conversations()), 3)
        publish = restore_activation.atomic_write

        def after_effect(*args, **kwargs):
            publish(*args, **kwargs)
            raise OSError('Acknowledgement failed')

        with patch.object(restore_activation, 'atomic_write', after_effect), self.assertRaises(OSError):
            self.activate()
        self.assertEqual(read_pointer(self.config)['generation'], self.draft['id'])
        self.assertTrue(self.manager.restore_pending.is_set())
        self.restart()
        self.assertEqual([c['id'] for c in self.manager.store.conversations()], [self.chat])
        self.assertEqual(len(self.original.conversations()), 3)

    def test_actual_crash_before_or_after_pointer_publication_selects_only_completed_choice(self):
        for after in (False, True):
            self.manager.close(shutdown=True)
            self.owner.close()
            process = multiprocessing.get_context('spawn').Process(target=activation_crash,
                args=(self.config, self.draft, after))
            process.start()
            try:
                process.join(10)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 27)
            finally:
                if process.is_alive():
                    process.terminate()
                    process.join(3)
                process.close()
            self.restart()
            self.assertEqual(len(self.manager.store.conversations()), 1 if after else 3)
            self.assertFalse(self.manager.running)
        self.assertEqual(len(self.original.conversations()), 3)


@skipUnless(fixtures.HAS_API, 'Install desktop dependencies')
class ActivationAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_activation_drains_admitted_rename_and_fresh_rollback_includes_it(self):
        manager = self.client.app.state.manager
        chat = manager.store.conversation('Before rename')
        item = backups.create(manager, confirmed=True)
        draft = restores.prepare(manager, item['id'], item['sha256'], confirmed=True)
        entered, release = threading.Event(), threading.Event()
        original = manager.store.rename_conversation

        def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('Fixture rename not released')
            return original(*args, **kwargs)

        with patch.object(manager.store, 'rename_conversation', delayed), ThreadPoolExecutor(max_workers=2) as pool:
            rename = pool.submit(self.client.post, f'/conversations/{chat}/rename',
                                 headers=self.headers, json={'title': 'Admitted rename'})
            self.assertTrue(entered.wait(2))
            activation = pool.submit(self.client.post, '/restore/activate', headers=self.headers,
                json={'preparation': draft['id'], 'sha256': draft['database_sha256'], 'confirmed': True})
            gate = self.client.app.state.restore_gate
            try:
                with gate.condition:
                    self.assertTrue(gate.condition.wait_for(lambda: gate.exclusive, timeout=2))
                self.assertFalse(activation.done())
                self.assertEqual(self.client.post('/conversations', headers=self.headers, json={'title': 'Denied during restore'}).status_code, 409)
            finally:
                release.set()
            self.assertEqual(rename.result(timeout=5).status_code, 200)
            response = activation.result(timeout=5)
            self.assertEqual(response.status_code, 200, response.text)
        rollback = self.policy.state / 'backups' / (response.json()['rollback'] + '.sqlite3')
        with closing(sqlite3.connect(rollback)) as db:
            self.assertEqual(db.execute('SELECT title FROM conversations WHERE id=?', (chat,)).fetchone()[0], 'Admitted rename')

    def test_auth_validation_inspection_and_committed_selection_freeze_old_routes(self):
        manager = self.client.app.state.manager
        chat = manager.store.conversation('Saved API data')
        item = self.client.post('/backups', headers=self.headers, json={'confirmed': True}).json()
        rows = self.client.get('/backups', headers=self.headers).json()
        self.assertEqual(rows['items'][0]['id'], item['id'])
        self.assertEqual(self.client.get('/backups/' + item['id'], headers=self.headers).json()['sha256'], item['sha256'])
        draft = self.client.post('/restore/prepare', headers=self.headers,
            json={'backup': item['id'], 'sha256': item['sha256'], 'confirmed': True}).json()
        body = {'preparation': draft['id'], 'sha256': draft['database_sha256'], 'confirmed': True}
        self.assertEqual(self.client.post('/restore/activate', json=body).status_code, 401)
        self.assertEqual(self.client.post('/restore/activate', headers={**self.headers, 'Origin': 'https://bad.invalid'}, json=body).status_code, 403)
        for invalid in ({**body, 'destination': '../escape'}, {**body, 'preparation': '../escape'}, {**body, 'confirmed': 1}):
            self.assertEqual(self.client.post('/restore/activate', headers=self.headers, json=invalid).status_code, 422)
        self.assertEqual(self.client.post('/restore/activate', headers=self.headers,
            json={**body, 'confirmed': False}).status_code, 403)
        response = self.client.post('/restore/activate', headers=self.headers, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['restart_required'])
        self.assertEqual(self.client.get('/conversations', headers=self.headers).status_code, 409)
        self.assertEqual(self.client.post('/tasks', headers=self.headers, json={}).status_code, 409)
        self.assertEqual(self.client.get('/conversations').status_code, 401)
        health = self.client.get('/health', headers=self.headers).json()
        self.assertTrue(health['restore_pending'])
        self.assertFalse(health['ready'])
        self.assertEqual(manager.store.conversations()[0]['id'], chat)
        self.assertNotIn('Saved API data', response.text)


class ActivationProcessTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def test_new_agent_after_restore_uses_selected_history_approvals_and_artifact_store(self):
        original = self.manager.store
        item = backups.create(self.manager, confirmed=True)
        draft = restores.prepare(self.manager, item['id'], item['sha256'], confirmed=True)
        owner = StateOwner(self.config)
        try:
            restore_activation.activate(self.manager, owner, draft['id'], draft['database_sha256'],
                                        confirmed=True, require_restart=lambda: None)
            self.manager.close(shutdown=True)
        finally:
            owner.close()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        task = self.manager.start(self.conversation, 'Create reviewed file after restore', 'agent', 'fixture')
        self.wait_until(lambda: bool(self.manager.pending()))
        approval = self.manager.pending()[0]
        self.assertEqual(approval['action'], 'create_file')
        self.assertFalse((self.policy.root / 'review.txt').exists())
        self.manager.approve(task, approval['id'], True)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual((self.policy.root / 'review.txt').read_text(), 'reviewed')
        self.assertEqual(original.tasks(), [])
        self.assertEqual(self.manager.store.tasks()[0]['id'], task)
        self.assertEqual(self.manager.store.tasks()[0]['status'], 'reported')
        records = self.manager.store.verifications(task)
        self.assertEqual(len(records), 1)
        self.assertEqual((records[0]['kind'], records[0]['status']), ('artifact', 'passed'))
        self.assertEqual(self.manager.store.identity, draft['store_id'])
