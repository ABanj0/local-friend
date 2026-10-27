"""Actual restore/rollback/restart and event-store reset through the production runtime."""
import json
from unittest import skipUnless
from urllib.error import HTTPError
from urllib.request import Request

from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


@skipUnless(HAS_SOCKET, 'Install desktop dependencies')
class ActivationHTTPTests(StudioSocketFixture, WorkspaceTest):
    def post(self, path, body):
        request = Request(f'http://127.0.0.1:{self.port}{path}', data=json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
                     'Origin': 'http://tauri.localhost'})
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def test_actual_activation_rollback_restart_and_stale_event_cursor_reset(self):
        from websockets.exceptions import ConnectionClosed

        chat = self.store.tasks()[0]['conversation']
        self.store.event(self.task, 'progress', {'text': 'Saved event'})
        item = self.post('/backups', {'confirmed': True})
        newer = self.store.conversation('Newer before activation')
        self.store.event(self.task, 'progress', {'text': 'Newer event'})
        draft = self.post('/restore/prepare', {'backup': item['id'], 'sha256': item['sha256'], 'confirmed': True})
        old_identity = self.store.identity
        old_cursor = self.store.event_high_water()
        with self.connect() as socket:
            socket.send(json.dumps({'token': self.token}))
            while True:
                frame = json.loads(socket.recv(timeout=3))
                socket.send(json.dumps({'ack': frame['delivery']}))
                if frame['kind'] == 'ready':
                    break
            selected = self.post('/restore/activate', {'preparation': draft['id'],
                'sha256': draft['database_sha256'], 'confirmed': True})
            self.assertTrue(selected['restart_required'])
            with self.assertRaises(ConnectionClosed) as closed:
                socket.recv(timeout=3)
            self.assertEqual(closed.exception.rcvd.code, 1012)
        with self.assertRaises(HTTPError) as blocked:
            self.http('/conversations')
        self.assertEqual(blocked.exception.code, 409)
        self.assertTrue(self.http('/health')['restore_pending'])
        self.stop_backend()
        self.start_backend()
        self.assertEqual(self.http(f'/history/conversations/{chat}')['id'], chat)
        with self.assertRaises(HTTPError) as missing:
            self.http(f'/history/conversations/{newer}')
        self.assertEqual(missing.exception.code, 404)
        self.assertEqual(self.http('/restore/status')['generation'], draft['id'])
        self.assertFalse(self.http('/health')['restore_pending'])
        with self.connect() as socket:
            socket.send(json.dumps({'token': self.token, 'after': old_cursor, 'store_id': old_identity}))
            snapshot = json.loads(socket.recv(timeout=3))
            self.assertEqual(snapshot['kind'], 'snapshot')
            self.assertTrue(snapshot['payload']['reset'])
            self.assertEqual(snapshot['payload']['store_id'], draft['store_id'])
            self.assertEqual([event['seq'] for event in snapshot['payload']['events']], [1])
            socket.send(json.dumps({'ack': snapshot['delivery']}))
        inspected = self.http('/backups/' + selected['rollback'])
        undo = self.post('/restore/prepare', {'backup': inspected['id'], 'sha256': inspected['sha256'], 'confirmed': True})
        self.post('/restore/activate', {'preparation': undo['id'], 'sha256': undo['database_sha256'], 'confirmed': True})
        self.stop_backend()
        self.start_backend()
        self.assertEqual(self.http(f'/history/conversations/{newer}')['id'], newer)
        self.assertEqual(len(self.http('/tasks')['tasks']), 1)
        self.assertEqual(len(self.store.conversations()), 2)  # Original DB was preserved too.
        self.assertFalse((self.policy.root / 'review.txt').exists())
