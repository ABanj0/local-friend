"""Backend state ownership, fail-closed generation lookup and restore request draining."""
import json
import os
import threading
from unittest import skipUnless

from local_agent.safety import Denied
from local_agent.studio.restore_gate import RestoreGate
from local_agent.studio.state_owner import POINTER, StateOwner, database_path, read_pointer
from local_agent.studio.store import Store

from . import studio_support as fixtures
from .support import WorkspaceTest


class StateOwnerTests(WorkspaceTest):
    def pointer(self, **changes):
        value = {'version': 1, 'generation': 'a' * 32, 'store_id': 'b' * 32,
                 'rollback': 'c' * 32, 'rollback_sha256': 'd' * 64}
        value.update(changes)
        (self.policy.state / POINTER).write_text(json.dumps(value))
        return value

    def test_exclusive_owner_reopens_same_lock_after_close_without_overwrite(self):
        first = StateOwner(self.config)
        self.addCleanup(first.close)
        path = self.policy.state / 'studio-owner.lock'
        identity = path.stat().st_ino
        with self.assertRaisesRegex(OSError, 'Another backend'):
            StateOwner(self.config)
        first.close()
        second = StateOwner(self.config)
        self.addCleanup(second.close)
        second.close()
        self.assertEqual(path.read_bytes(), b'1')
        self.assertEqual(path.stat().st_ino, identity)
        second.close()

    def test_invalid_and_hardlinked_ownership_files_are_preserved(self):
        path = self.policy.state / 'studio-owner.lock'
        path.write_bytes(b'KEEP UNKNOWN')
        with self.assertRaises(Denied):
            StateOwner(self.config)
        self.assertEqual(path.read_bytes(), b'KEEP UNKNOWN')
        path.write_bytes(b'1')
        alias = self.policy.state / 'alias'
        os.link(path, alias)
        with self.assertRaises(Denied):
            StateOwner(self.config)
        self.assertEqual(alias.read_bytes(), b'1')
        alias.unlink()

    def test_default_path_selected_generation_and_stop_latched_history(self):
        original = Store(self.policy.state / 'studio.sqlite3')
        original.conversation('Original retained')
        self.assertEqual(database_path(self.config), original.path)
        self.assertIsNone(read_pointer(self.config))
        selected = Store(self.policy.state / 'restore-staging' / ('a' * 32) / 'studio.sqlite3')
        selected.conversation('Selected generation')
        self.pointer(store_id=selected.identity)
        self.assertEqual(database_path(self.config), selected.path)
        (self.policy.state / 'STOP').touch()
        self.assertEqual(database_path(self.config), selected.path)
        self.assertEqual(original.conversations()[0]['title'], 'Original retained')

    def test_malformed_pointer_never_creates_or_falls_back_to_an_empty_database(self):
        path = self.policy.state / POINTER
        for raw in (b'not json', b'{}', b'x' * 4097):
            path.write_bytes(raw)
            with self.assertRaises((ValueError, Denied)):
                database_path(self.config)
            self.assertFalse((self.policy.state / 'studio.sqlite3').exists())
        for changes in ({'generation': '../outside'}, {'generation': 'C:\\private'}, {'version': True},
                        {'extra': 'not allowed'}, {'rollback_sha256': 'bad'}):
            self.pointer(**changes)
            with self.assertRaises(ValueError):
                database_path(self.config)
        self.assertFalse((self.policy.state / 'studio.sqlite3').exists())

    def test_dangling_changed_identity_and_linked_generation_are_refused(self):
        self.pointer()
        with self.assertRaisesRegex(ValueError, 'missing'):
            database_path(self.config)
        selected = Store(self.policy.state / 'restore-staging' / ('a' * 32) / 'studio.sqlite3')
        with self.assertRaisesRegex(ValueError, 'identity'):
            database_path(self.config)
        self.pointer(store_id=selected.identity)
        alias = self.policy.state / 'alias.sqlite3'
        os.link(selected.path, alias)
        with self.assertRaises(Denied):
            database_path(self.config)
        alias.unlink()
        os.link(self.policy.state / POINTER, self.policy.state / 'pointer-alias')
        with self.assertRaises(Denied):
            database_path(self.config)

    @skipUnless(fixtures.HAS_API, 'Install desktop dependencies')
    def test_failed_application_startup_releases_owner_and_retains_original_data(self):
        from fastapi.testclient import TestClient

        from local_agent.studio.api import create_app

        original = Store(self.policy.state / 'studio.sqlite3')
        original.conversation('Keep original data')
        self.pointer()  # Valid pointer shape, missing generation.
        with self.assertRaisesRegex(ValueError, 'missing'):
            create_app(self.config, 'z' * 64)
        (self.policy.state / POINTER).unlink()  # Remove only this fixture's rejected selection.
        with TestClient(create_app(self.config, 'z' * 64)) as client:
            response = client.get('/conversations', headers={'Authorization': 'Bearer ' + 'z' * 64})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]['title'], 'Keep original data')


class RestoreGateTests(WorkspaceTest):
    def test_freeze_drains_prior_request_refuses_new_work_and_stays_pending_until_restart(self):
        gate = RestoreGate()
        self.assertTrue(gate.enter())  # Activation request.
        self.assertTrue(gate.enter())  # Existing authenticated request.
        ready, finished = threading.Event(), threading.Event()

        def activate():
            with gate.freeze():
                ready.set()
                gate.require_restart()
            finished.set()

        worker = threading.Thread(target=activate)
        worker.start()
        try:
            with gate.condition:
                self.assertTrue(gate.condition.wait_for(lambda: gate.exclusive, timeout=2))
            self.assertFalse(ready.wait(.05))
            self.assertFalse(gate.enter())
            gate.leave()
            self.assertTrue(finished.wait(2))
            self.assertTrue(ready.is_set())
            self.assertFalse(gate.enter())
        finally:
            worker.join(2)
            gate.leave()
        self.assertFalse(worker.is_alive())

    def test_drain_timeout_and_failed_action_release_gate_without_losing_requests(self):
        gate = RestoreGate()
        gate.enter()
        gate.enter()
        with self.assertRaises(TimeoutError), gate.freeze(timeout=.01):
            self.fail('Must drain other requests before entering')
        self.assertTrue(gate.enter())
        gate.leave()
        gate.leave()
        with self.assertRaisesRegex(ValueError, 'Injected'), gate.freeze():
            raise ValueError('Injected failure')
        self.assertTrue(gate.enter())
        gate.leave()
        gate.leave()
        self.assertEqual(gate.requests, 0)


@skipUnless(fixtures.HAS_API, 'Install desktop dependencies')
class StateOwnerAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_duplicate_app_refused_before_recovery_and_pending_routes_remain_authenticated(self):
        from local_agent.studio.api import create_app

        manager = self.client.app.state.manager
        chat = manager.store.conversation('Retained current state')
        task = manager.store.task(chat, 'agent', 'fixture')
        with self.assertRaisesRegex(OSError, 'Another backend'):
            create_app(self.config, 'y' * 64)
        self.assertEqual(manager.store.tasks()[0]['status'], 'running')
        manager.store.finish(task, 'reported', {'report': 'Retained'})
        self.client.app.state.restore_gate.require_restart()
        self.assertEqual(self.client.get('/conversations').status_code, 401)
        self.assertEqual(self.client.get('/conversations', headers=self.headers).status_code, 409)
        self.assertEqual(self.client.post('/tasks', json={}, headers=self.headers).status_code, 409)
        self.assertEqual(self.client.get('/health', headers=self.headers).status_code, 200)
