"""Real backend state lease, duplicate startup and abrupt-exit recovery."""
import json
import os
import subprocess
from unittest import skipUnless

from .runtime_command import runtime_command
from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


@skipUnless(HAS_SOCKET, 'Install desktop dependencies')
class StateOwnerHTTPTests(StudioSocketFixture, WorkspaceTest):
    def test_duplicate_port_zero_backend_cannot_recover_first_state_and_crash_releases_lease(self):
        # Seed an orphan-active row explicitly; waiting() correctly ignores terminal rows.
        with self.store.connection() as db:
            db.execute("UPDATE tasks SET status='waiting',result=NULL WHERE id=?", (self.task,))
        self.assertEqual(self.store.tasks()[0]['status'], 'waiting')
        second = subprocess.run([*runtime_command(), '--config', str(self.socket_config), '--port', '0'],
            check=False,
            env=dict(os.environ, LOCAL_AGENT_STUDIO_TOKEN='separate-runtime-token-' * 3),
            input='', capture_output=True, text=True, timeout=8)
        self.assertEqual(second.returncode, 1, second.stdout)
        self.assertIn('Another backend owns', json.loads(second.stdout)['error'])
        self.assertNotIn('Traceback', second.stderr)
        self.assertEqual(self.store.tasks()[0]['status'], 'waiting')
        self.assertTrue(self.http('/health')['ready'])
        # Terminate only this fixture's backend, with no owned worker/model involved.
        self.proc.terminate()
        self.proc.wait(5)
        self.stop_backend()
        self.start_backend()
        self.assertTrue(self.http('/health')['ready'])
        self.assertEqual(self.store.tasks()[0]['status'], 'interrupted')
