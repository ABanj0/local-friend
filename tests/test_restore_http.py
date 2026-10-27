"""Actual runtime HTTP and restart: preparation never activates the draft."""
import json
import sqlite3
from contextlib import closing
from unittest import skipUnless
from urllib.request import Request

from local_agent.studio.restores import validate_schema

from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


@skipUnless(HAS_SOCKET, 'Install desktop dependencies')
class RestoreHTTPTests(StudioSocketFixture, WorkspaceTest):
    def post(self, path, body):
        request = Request(f'http://127.0.0.1:{self.port}{path}', data=json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
                     'Origin': 'http://tauri.localhost'})
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def test_real_runtime_prepares_and_restarts_without_activating_or_replaying(self):
        item = self.post('/backups', {'confirmed': True})
        newer = self.store.conversation('Current retained after preparation')
        before_events = self.store.event_high_water()
        prepared = self.post('/restore/prepare', {'backup': item['id'], 'sha256': item['sha256'], 'confirmed': True})
        self.assertFalse(prepared['activated'])
        self.assertEqual(prepared['original_store_id'], self.store.identity)
        target = self.policy.state / 'restore-staging' / prepared['id'] / 'studio.sqlite3'
        with closing(sqlite3.connect(target)) as db:
            self.assertEqual(validate_schema(db), prepared['store_id'])
            self.assertIsNone(db.execute('SELECT id FROM conversations WHERE id=?', (newer,)).fetchone())
        rollback = self.policy.state / 'backups' / (prepared['rollback'] + '.sqlite3')
        with closing(sqlite3.connect(rollback)) as db:
            self.assertIsNotNone(db.execute('SELECT id FROM conversations WHERE id=?', (newer,)).fetchone())
        self.assertEqual(self.http(f'/history/conversations/{newer}')['id'], newer)
        self.stop_backend()
        self.start_backend()
        self.assertEqual(self.http(f'/history/conversations/{newer}')['id'], newer)
        self.assertEqual(len(self.http('/tasks')['tasks']), 1)
        self.assertEqual(self.store.event_high_water(), before_events)
        self.assertFalse((self.policy.root / 'review.txt').exists())
