"""Manual retention through the actual runtime, including restart and websocket privacy."""
import json
from unittest import skipUnless
from urllib.error import HTTPError
from urllib.request import Request

from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


@skipUnless(HAS_SOCKET, 'Install desktop dependencies')
class RetentionHTTPTests(StudioSocketFixture, WorkspaceTest):
    def post(self, path, body):
        request = Request(f'http://127.0.0.1:{self.port}{path}', data=json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
                     'Origin': 'http://tauri.localhost'})
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def test_confirmed_batch_cascades_survives_restart_and_never_replays_review(self):
        old = self.store.tasks()[0]['conversation']
        self.store.message(old, 'user', 'RETENTION-HTTP-PRIVATE')
        with self.store.connection() as db:
            for table in ('conversations', 'messages', 'tasks'):
                db.execute(f'UPDATE {table} SET created=1')
        keep = self.store.conversation('Kept selected conversation')
        self.post('/retention/policy', {'older_than_days': 1, 'keep_recent': 0, 'batch_size': 2})
        preview = self.post('/retention/preview', {'protected': [keep]})
        self.assertEqual([row['id'] for row in preview['items']], [old])
        self.assertNotIn('RETENTION-HTTP-PRIVATE', json.dumps(preview))
        with self.assertRaises(HTTPError) as denied:
            self.post('/retention/apply', {'preview': preview['id'], 'confirmed': False})
        self.assertEqual(denied.exception.code, 403)
        self.assertEqual(len(self.store.conversations()), 2)
        result = self.post('/retention/apply', {'preview': preview['id'], 'confirmed': True})
        self.assertEqual(result['counts']['tasks'], 1)
        self.assertEqual(result['counts']['messages'], 1)
        self.assertEqual(result['deleted'], 1)
        self.stop_backend()
        self.start_backend()
        self.assertEqual(self.http('/retention')['last_action'], result)
        self.assertEqual(self.http('/retention')['policy']['batch_size'], 2)
        self.assertEqual([row['id'] for row in self.http('/conversations')], [keep])
        self.assertEqual(self.http('/tasks')['tasks'], [])
        with self.assertRaises(HTTPError) as expired:
            self.post('/retention/apply', {'preview': preview['id'], 'confirmed': True})
        self.assertEqual(expired.exception.code, 400)
        with self.connect() as socket:
            socket.send(json.dumps({'token': self.token}))
            snapshot = json.loads(socket.recv(timeout=3))
            self.assertEqual(snapshot['payload']['events'], [])
            self.assertNotIn('RETENTION-HTTP-PRIVATE', json.dumps(snapshot))
        self.assertFalse((self.policy.root / 'review.txt').exists())
