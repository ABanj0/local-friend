"""Real HTTP protocol/spawned worker, verifying live state and final SQLite bytes."""
import threading

from local_agent.redaction import redact_text

from .studio_support import StudioProcessFixture
from .support import WorkspaceTest


class StreamPrivacyTests(StudioProcessFixture, WorkspaceTest):
    def setUp(self):
        self.stream_chunks = []
        self.stream_final_gate = threading.Event()
        super().setUp()
        self.addCleanup(self.stream_final_gate.set)

    def stream(self):
        return ''.join(e["payload"]["text"] for e in self.manager.live_events if e["kind"] == "token")

    def assert_no_leak(self):
        self.assertNotIn('CANARY', str(self.manager.live_events))
        self.assertNotIn('CANARY', str(self.manager.store.messages(self.conversation)))
        self.assertNotIn('CANARY', str(self.manager.store.events()))
        for path in self.policy.state.glob('studio.sqlite3*'):
            self.assertNotIn(b'CANARY', path.read_bytes())

    def test_live_state_and_stored_report_agree_before_and_after_completion(self):
        text = ('ordinary streaming text ' * 5 + '\npassword=CANARY-one; ' +
                '{"token":"CANARY-two escaped\\\" body"} Bearer CANARY-three\n' +
                '-----BEGIN PRIVATE KEY-----\nCANARY-four\n-----END PRIVATE KEY-----\nend')
        self.stream_chunks.extend(text)  # Single characters stress every boundary.
        self.manager.start(self.conversation, "Protocol privacy fixture", "chat", "fixture")
        self.wait_until(lambda: "[REDACTED]" in self.stream())
        self.assertTrue(self.manager.running, "Final response is deliberately gated")
        self.assertIn('ordinary streaming text', self.stream())
        self.assert_no_leak()
        self.stream_final_gate.set()
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.stream(), redact_text(text))
        self.assertEqual(self.manager.store.messages(self.conversation)[-1]["content"], self.stream())
        self.assert_no_leak()

    def test_cancelled_partial_secret_never_leaves_live_or_durable_output(self):
        self.stream_chunks.extend('normal text ' * 4 + 'password=CANARY-unfinished')
        task = self.manager.start(self.conversation, "Protocol cancellation fixture", "chat", "fixture")
        self.wait_until(lambda: '[REDACTED]' in self.stream())
        self.manager.cancel(task)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.store.tasks()[0]["status"], 'cancelled')
        self.assert_no_leak()
