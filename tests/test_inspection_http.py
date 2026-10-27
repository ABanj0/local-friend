"""Actual runtime pause/restart/resume and crash recovery; inference is a protocol fixture."""
import json
import subprocess
import sys
from unittest import skipUnless
from urllib.error import HTTPError
from urllib.request import Request

from .inspection_support import InspectionModelFixture
from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


@skipUnless(HAS_SOCKET, 'Install desktop dependencies')
class InspectionHTTPTests(StudioSocketFixture, InspectionModelFixture, WorkspaceTest):
    def start_backend(self):
        source = self.socket_config.read_text(encoding='utf-8')
        source = source.replace('url = "http://127.0.0.1:11434"', 'url = ' + json.dumps(self.config['model']['url']))
        self.socket_config.write_text(source, encoding='utf-8')
        super().start_backend()

    def post(self, path, body):
        request = Request(f'http://127.0.0.1:{self.port}{path}', data=json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
                     'Origin': 'http://tauri.localhost'})
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def begin(self):
        self.gate.clear()
        chat = self.store.tasks()[0]['conversation']
        self.store.message(chat, 'user', 'FORBIDDEN-HISTORY-CANARY')
        task = self.post('/inspections', {'conversation': chat, 'objective': 'Inspect selected code',
            'model': self.config['model']['name'], 'project': '.', 'files': ['a.py', 'b.py']})['id']
        self.wait_until(lambda: self.entered.is_set())
        self.assertEqual(self.http(f'/tasks/{task}/inspection')['completed_step'], 1)
        self.assertNotIn('FORBIDDEN-HISTORY-CANARY', json.dumps(self.requests))
        self.assertEqual({item['function']['name'] for item in self.requests[-1]['tools']}, {'read_file'})
        return task

    def test_acknowledged_pause_survives_runtime_restart_and_resumes_as_linked_task(self):
        task = self.begin()
        with self.assertRaises(HTTPError) as forbidden:
            self.post(f'/tasks/{task}/inspection/pause', {'approved': True})
        self.assertEqual(forbidden.exception.code, 422)
        self.assertEqual(self.post(f'/tasks/{task}/inspection/pause', {}), {'requested': True, 'paused': False})
        self.gate.set()
        self.wait_until(lambda: self.http(f'/tasks/{task}/inspection')['can_resume'])
        self.stop_backend()
        self.start_backend()
        self.assertEqual(self.http(f'/tasks/{task}/inspection')['state'], 'paused')
        before = len(self.requests)
        resumed = self.post(f'/tasks/{task}/inspection/resume', {})['id']
        self.wait_until(lambda: self.http('/tasks')['tasks'][0]['status'] == 'reported')
        self.assertEqual(len(self.requests) - before, 1)
        self.assertEqual(self.http(f'/tasks/{resumed}/inspection')['source_task'], task)
        self.assertEqual(self.http(f'/tasks/{resumed}/journal')['operations'], [])
        self.assertEqual(self.http(f'/tasks/{task}/inspection')['resumed_by'], resumed)
        with self.assertRaises(HTTPError) as stale:
            self.post(f'/tasks/{task}/inspection/resume', {})
        self.assertEqual(stale.exception.code, 400)
        self.assertFalse((self.policy.root / 'artifact.txt').exists())

    def test_real_backend_crash_preserves_last_completed_boundary_and_unrelated_process(self):
        task = self.begin()
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(45)'])

        def close_unrelated():
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(3)

        self.addCleanup(close_unrelated)
        # One-file builds have a launcher and a runtime child. Kill the actual owned
        # listener, otherwise closing the launcher can cause a graceful stdin/EOF cancel.
        import psutil
        launcher = psutil.Process(self.proc.pid)
        owned = [launcher, *launcher.children(recursive=True)]
        listeners = [process for process in owned if any(
            connection.status == psutil.CONN_LISTEN and connection.laddr.ip == '127.0.0.1'
            and connection.laddr.port == self.port for connection in process.net_connections(kind='tcp'))]
        self.assertEqual(len(listeners), 1, 'Expected exactly one listener in the fixture-owned process tree')
        print('Inspection crash target: ' + json.dumps({'runtime_is_launcher': listeners[0].pid == self.proc.pid,
                                                        'owned_listeners': len(listeners)}), flush=True)
        listeners[0].kill()  # Its Job Object owns its worker; no name/global process kill.
        listeners[0].wait(5)
        self.proc.wait(5)
        self.stop_backend()
        self.gate.set()
        self.start_backend()
        self.assertIsNone(unrelated.poll())
        self.assertEqual(self.store.tasks()[0]['status'], 'interrupted')
        self.assertEqual(self.http(f'/tasks/{task}/inspection')['completed_step'], 1)
        resumed = self.post(f'/tasks/{task}/inspection/resume', {})['id']
        self.wait_until(lambda: self.http('/tasks')['tasks'][0]['status'] == 'reported')
        operations = self.http(f'/tasks/{resumed}/journal')['operations']
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]['tool'], 'read_file')
        self.assertEqual(operations[0]['effect'], 'read')
        self.assertIsNone(unrelated.poll())
        unrelated.kill()
        unrelated.wait(3)
