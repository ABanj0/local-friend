import os
import sqlite3
import time
import unittest
from contextlib import closing

from local_agent.studio.manager import Manager
from local_agent.studio.store import Store

from . import studio_support as fixtures
from .support import WorkspaceTest


class StudioStoreTests(WorkspaceTest):
    def test_legacy_messages_migrate_without_loss_and_metrics_persist(self):
        path = self.policy.state / "legacy.db"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE messages(id TEXT PRIMARY KEY, conversation TEXT, role TEXT, content TEXT, created REAL)")
            db.execute("INSERT INTO messages VALUES ('old','conversation','assistant','kept',1)")
        store = Store(path)
        with store.connection() as db:
            db.execute("INSERT INTO conversations(id,title,created) VALUES ('conversation','Existing',1)")
        self.assertEqual(store.messages("conversation")[0]["content"], "kept")
        self.assertIsNone(store.messages("conversation")[0]["metrics"])
        metrics = {"generated_tokens": 80, "tokens_per_second": 40, "elapsed_seconds": 3,
                   "model_calls": 1, "scope": "response"}
        store.message("conversation", "assistant", "new", metrics)
        self.assertEqual(Store(path).messages("conversation")[-1]["metrics"], metrics)

    def test_persistence_redaction_and_recovery(self):
        path = self.policy.state / "sessions.db"
        store = Store(path)
        conversation = store.conversation("Example")
        store.message(conversation, "user", "hello")
        task = store.task(conversation, "chat", "local")
        store.event(task, "approval", {"secret": "do not persist this"})
        reopened = Store(path)
        self.assertEqual(reopened.messages(conversation)[0]["content"], "hello")
        self.assertEqual(reopened.events()[0]["payload"], {"transient": True})
        reopened.recover()
        self.assertEqual(reopened.tasks()[0]["status"], "interrupted")

    def test_conversation_isolation_and_event_cursor(self):
        store = Store(self.policy.state / "sessions.db")
        first, second = store.conversation(), store.conversation()
        store.message(first, "user", "first")
        self.assertEqual(store.messages(second), [])
        with self.assertRaises(KeyError):
            store.messages("missing")
        task = store.task(first, "agent", "local")
        event = store.event(task, "plan", {"steps": ["inspect"]})
        self.assertEqual(store.events(event["seq"]), [])
        store.finish(task, "reported", {"report": "verified"})
        self.assertEqual(store.tasks()[0]["status"], "reported")

    def test_preferences_and_structured_secret_redaction(self):
        from local_agent.agent import clean
        store = Store(self.policy.state / "sessions.db")
        store.preferences({"model": "other", "context": 4096})
        self.assertEqual(Store(store.path).preferences()["model"], "other")
        self.assertEqual(clean({"password": "private"}), {"password": "[REDACTED]"})
        self.assertNotIn("private", clean('{"password": "private"}'))


class StudioProcessTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def test_approved_action_is_bound_to_task_and_not_reusable(self):
        task = self.manager.start(self.conversation, "write", "agent", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        request = self.manager.pending()[0]
        self.assertFalse((self.policy.root / "review.txt").exists())
        with self.assertRaises(ValueError):
            self.manager.approve("another-task", request["id"], True)
        self.manager.approve(task, request["id"], True)
        with self.assertRaises(ValueError):
            self.manager.approve(task, request["id"], True)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual((self.policy.root / "review.txt").read_text(), "reviewed")
        self.assertEqual(self.manager.store.tasks()[0]["status"], "reported")
        metrics = self.manager.store.messages(self.conversation)[-1]["metrics"]
        self.assertEqual(metrics["generated_tokens"], 30)
        self.assertEqual(metrics["tokens_per_second"], 20)
        self.assertEqual(metrics["scope"], "task")
        self.assertEqual(metrics["model_calls"], 3)

    def test_denied_action_does_not_write(self):
        task = self.manager.start(self.conversation, "write", "agent", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.manager.approve(task, self.manager.pending()[0]["id"], False)
        self.wait_until(lambda: not self.manager.running)
        self.assertFalse((self.policy.root / "review.txt").exists())
        self.assertEqual(self.manager.store.tasks()[0]["status"], "blocked")

    def test_streaming_protocol_and_persistence(self):
        self.manager.start(self.conversation, "hello", "chat", "fixture")
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.store.messages(self.conversation)[-1]["content"], "hello world")
        metrics = self.manager.store.messages(self.conversation)[-1]["metrics"]
        self.assertEqual(metrics["generated_tokens"], 80)  # Not the two streaming chunks.
        self.assertEqual(metrics["tokens_per_second"], 40)
        self.assertEqual(metrics["scope"], "response")
        self.assertGreater(metrics["elapsed_seconds"], 0)
        streamed = [e["payload"]["text"] for e in self.manager.live_events if e["kind"] == "token"]
        self.assertTrue(streamed)
        self.assertEqual("".join(streamed), "hello world")
        self.assertFalse(any(e["kind"] == "token" for e in self.manager.store.events()))


@unittest.skipUnless(fixtures.HAS_API, "Desktop API dependencies not installed")
class StudioAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_authentication_and_origin(self):
        self.assertEqual(self.client.get("/health").status_code, 401)
        self.assertEqual(self.client.get("/health", headers=self.headers).status_code, 200)
        headers = dict(self.headers, Origin="https://attacker.invalid")
        self.assertEqual(self.client.get("/health", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/emergency-stop").status_code, 401)

    def test_scoped_files_and_persistence(self):
        response = self.client.post("/conversations", json={"title": "Test"}, headers=self.headers)
        ident = response.json()["id"]
        self.assertEqual(self.client.get(f"/conversations/{ident}/messages", headers=self.headers).json(), [])
        self.assertEqual(self.client.get("/file", params={"path": "../secret"}, headers=self.headers).status_code, 403)
        self.assertEqual(self.client.post("/project", json={"path": ".."}, headers=self.headers).status_code, 403)

    def test_socket_credentials_and_snapshot(self):
        from starlette.websockets import WebSocketDisconnect
        with self.assertRaises(WebSocketDisconnect), self.client.websocket_connect(
            "/events", headers={"Origin": "https://attacker.invalid"}
        ):
            pass
        with self.client.websocket_connect("/events", headers={"Origin": "http://tauri.localhost"}) as socket:
            socket.send_json({"token": "x" * 64})
            self.assertEqual(socket.receive_json()["kind"], "snapshot")


@unittest.skipUnless(os.environ.get("LIVE_STUDIO") == "1", "Set LIVE_STUDIO=1 for real Ollama worker tests")
class StudioLiveTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)

    def wait(self, timeout=180):
        deadline = time.monotonic() + timeout
        while self.manager.running and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertFalse(self.manager.running, "Worker did not exit before timeout")

    def test_real_stream_and_context(self):
        conversation = self.manager.store.conversation()
        self.manager.store.message(conversation, "user", "Remember the marker ORCHID731.")
        self.manager.store.message(conversation, "assistant", "I will remember it.")
        self.manager.start(conversation, "Reply only with the marker I asked you to remember.",
                           "chat", self.config["model"]["name"])
        self.wait()
        messages = self.manager.store.messages(conversation)
        self.assertIn("ORCHID731", messages[-1]["content"])
        self.assertGreater(messages[-1]["metrics"]["generated_tokens"], 0)
        self.assertGreater(messages[-1]["metrics"]["tokens_per_second"], 0)
        self.assertTrue(any(e["kind"] == "token" for e in self.manager.live_events))
        self.assertEqual(self.manager.store.tasks()[0]["status"], "reported")

    def test_cancel_real_worker(self):
        conversation = self.manager.store.conversation()
        task = self.manager.start(conversation, "Write a long explanation of arithmetic.",
                                  "chat", self.config["model"]["name"])
        self.manager.cancel(task)
        self.wait(10)
        self.assertEqual(self.manager.store.tasks()[0]["status"], "cancelled")

    def test_real_agent_read_and_report(self):
        (self.policy.root / "studio-evidence.txt").write_text("VERIFIED-731", encoding="utf-8")
        conversation = self.manager.store.conversation()
        self.manager.start(conversation, "Read studio-evidence.txt using read_file and report its exact contents.",
                           "agent", self.config["model"]["name"])
        self.wait()
        events = self.manager.live_events
        self.assertTrue(any(e["kind"] == "tool_result" and e["payload"]["name"] == "read_file"
                            and e["payload"]["result"]["ok"] for e in events))
        self.assertIn("VERIFIED-731", self.manager.store.messages(conversation)[-1]["content"])
