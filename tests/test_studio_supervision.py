"""Real owned workers under pipe, storage, approval, deadline and cancellation faults."""
import json
import os
import sqlite3
import threading
import time
import unittest
from unittest.mock import patch

from local_agent.studio.manager import Manager

from . import studio_support as fixtures
from .lifecycle_worker import lifecycle_worker
from .support import WorkspaceTest


class StudioSupervisionTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.thread_errors = self.enterContext(patch("threading.excepthook"))

    def start(self, mode="agent", objective="Write the reviewed fixture file"):
        with self.manager.lock:
            task = self.manager.start(self.conversation, objective, mode, "fixture")
            state = self.manager.running[task]
        return task, state

    def settled(self, task, state, status):
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.store.tasks()[0]["status"], status)
        terminal = [e for e in self.manager.store.events() if e["task"] == task and e["kind"] == "result"]
        self.assertEqual(len(terminal), 1)
        self.assertEqual(terminal[0]["payload"], json.loads(self.manager.store.tasks()[0]["result"]))
        self.assertEqual(len([m for m in self.manager.store.messages(self.conversation)
                              if m["role"] == "assistant"]), 1)
        self.assertEqual(self.manager.pending(), [])
        self.assertTrue(state["pipe"].closed)
        self.assertTrue(state["process_closed"])
        with self.assertRaises(ValueError):
            state["process"].is_alive()
        if state["job"]:
            self.assertIsNone(state["job"].handle)
        self.thread_errors.assert_not_called()
        return terminal[0]["payload"]

    def test_poll_failure_stops_and_completes_worker(self):
        with self.manager.lock:
            task, state = self.start()
            self.enterContext(patch.object(state["pipe"], "poll",
                                          side_effect=OSError("token=monitor-poll-canary")))
        result = self.settled(task, state, "failed")
        self.assertNotIn("monitor-poll-canary", result["report"])
        self.assertFalse((self.policy.root / "review.txt").exists())

    def test_recv_failure_stops_and_completes_worker(self):
        with self.manager.lock:
            task, state = self.start()
            self.enterContext(patch.object(state["pipe"], "recv", side_effect=EOFError("fixture EOF")))
        self.settled(task, state, "failed")

    def test_eof_lookahead_preserves_an_already_received_terminal_frame(self):
        received_result = threading.Event()
        with self.manager.lock:
            task, state = self.start("chat", "Finish and close the worker pipe")
            original_recv, original_poll = state["pipe"].recv, state["pipe"].poll

            def recv():
                event = original_recv()
                if event["kind"] == "result":
                    received_result.set()
                return event

            def poll(*args):
                if received_result.is_set():
                    raise BrokenPipeError("Injected Windows EOF after final frame")
                return original_poll(*args)

            self.enterContext(patch.object(state["pipe"], "recv", side_effect=recv))
            self.enterContext(patch.object(state["pipe"], "poll", side_effect=poll))
        self.settled(task, state, "reported")
        self.assertTrue(received_result.is_set())

    def test_event_storage_failure_stops_worker_without_duplicate_result(self):
        original = self.manager.store.event

        def event(task, kind, payload):
            if kind == "worker_ready":
                raise sqlite3.OperationalError("token=event-storage-canary")
            return original(task, kind, payload)

        with patch.object(self.manager.store, "event", side_effect=event):
            task, state = self.start()
            result = self.settled(task, state, "failed")
        self.assertNotIn("event-storage-canary", result["report"])

    def test_transient_completion_fault_is_retried_without_replaying_work(self):
        original = self.manager.store.complete
        attempts = []

        def complete(task, result):
            attempts.append(task)
            if len(attempts) == 1:
                raise sqlite3.OperationalError("token=terminal-storage-canary")
            return original(task, result)

        with patch.object(self.manager.store, "complete", side_effect=complete):
            task, state = self.start("chat", "Respond normally")
            self.settled(task, state, "reported")
        self.assertEqual(len(attempts), 2)
        self.assertEqual(len(self.requests), 1, "Persistence recovery must not replay model calls")
        self.assertNotIn("terminal-storage-canary", json.dumps(self.manager.live_events))

    @unittest.skipUnless(fixtures.HAS_API, "Desktop API dependencies not installed")
    def test_cancel_stops_worker_during_actual_sqlite_lock_and_recovers(self):
        from fastapi.testclient import TestClient

        from local_agent.studio.api import create_app
        task, state = self.start()
        self.wait_until(lambda: bool(self.manager.pending()))
        db = sqlite3.connect(self.manager.store.path)
        self.addCleanup(db.close)
        db.execute("BEGIN IMMEDIATE")
        headers = {"Authorization": "Bearer " + "z" * 64}
        with TestClient(create_app(self.config, "z" * 64, self.manager)) as client:
            started = time.monotonic()
            self.manager.cancel(task)
            self.assertLess(time.monotonic() - started, 1)
            self.wait_until(lambda: state.get("process_closed") and not self.manager.diagnostics()["ready"])
            self.assertLess(time.monotonic() - started, 5)
            self.assertEqual(self.manager.pending(), [])
            health = client.get("/health", headers=headers).json()
            self.assertFalse(health["ready"])
            self.assertEqual(health["task_errors"][0]["phase"], "storage")
            snapshot = client.get("/tasks", headers=headers).json()
            self.assertEqual(snapshot["tasks"][0]["runtime_state"], "storage")
            self.assertEqual(snapshot["approvals"], [])
            self.assertEqual(client.post("/conversations", headers=headers, json={"title": "Busy"}).status_code, 503)
            with self.assertRaises(ValueError):
                self.manager.start(self.conversation, "Do not replay", "chat", "fixture")
            db.rollback()
            self.settled(task, state, "cancelled")
            self.assertTrue(client.get("/health", headers=headers).json()["ready"])
            next_task, next_state = self.start("chat", "Explicit new request after storage recovered")
            self.wait_until(lambda: not self.manager.running)
            self.assertTrue(next_state["process_closed"])
            self.assertEqual(self.manager.store.tasks()[0]["id"], next_task)
            self.assertEqual(self.manager.store.tasks()[0]["status"], "reported")

    def test_failed_approval_delivery_does_not_execute_or_replay(self):
        task, state = self.start()
        self.wait_until(lambda: bool(self.manager.pending()))
        request = self.manager.pending()[0]
        with patch.object(state["pipe"], "send", side_effect=BrokenPipeError("token=approval-canary")):
            with self.assertRaises(OSError):
                self.manager.approve(task, request["id"], True)
            result = self.settled(task, state, "failed")
        self.assertFalse((self.policy.root / "review.txt").exists())
        self.assertNotIn("approval-canary", result["report"])
        with self.assertRaises(ValueError):
            self.manager.approve(task, request["id"], True)

    def test_readiness_deadline_stops_unresponsive_spawn(self):
        self.manager.limits["ready_timeout"] = 0.5
        with patch("local_agent.studio.manager.worker_main", lifecycle_worker):
            task, state = self.start(objective="not_ready")
        result = self.settled(task, state, "failed")
        self.assertIn("starting deadline", result["report"])

    def test_missing_heartbeat_stops_ready_worker(self):
        self.manager.limits["heartbeat_timeout"] = 0.5
        with patch("local_agent.studio.manager.worker_main", lifecycle_worker):
            task, state = self.start(objective="no_heartbeat")
        result = self.settled(task, state, "failed")
        self.assertIn("heartbeat lost", result["report"])

    def test_total_task_budget_is_not_reset_by_heartbeats_and_phases(self):
        self.manager.limits["task_timeout"] = 0.7
        with patch("local_agent.studio.manager.worker_main", lifecycle_worker):
            task, state = self.start(objective="continual_progress")
        result = self.settled(task, state, "failed")
        self.assertIn("task deadline", result["report"])

    def test_queued_heartbeats_survive_parent_dispatch_delay(self):
        self.manager.limits["heartbeat_timeout"] = 0.2
        with patch("local_agent.studio.manager.worker_main", lifecycle_worker):
            task, state = self.start(objective="delayed_result")
        self.wait_until(lambda: state["ready"])
        with self.manager.lock:
            time.sleep(0.6)
        time.sleep(0.15)
        self.assertFalse(state["done"], "Queued healthy heartbeats were ignored after parent dispatch delay")
        self.manager.cancel(task)
        self.settled(task, state, "cancelled")

    def test_invalid_terminal_event_is_a_single_failure(self):
        with patch("local_agent.studio.manager.worker_main", lifecycle_worker):
            task, state = self.start(objective="malformed")
        result = self.settled(task, state, "failed")
        self.assertIn("invalid terminal", result["report"])

    def test_invalid_goal_result_does_not_strand_completion(self):
        self.manager.store.create_goal(self.conversation, "Fixture goal")
        with patch("local_agent.studio.manager.worker_main", lifecycle_worker):
            task, state = self.start(objective="bad_terminal")
        result = self.settled(task, state, "failed")
        self.assertIn("Completion failed", result["report"])
        self.assertEqual(self.manager.store.current_goal(self.conversation)["steps"], [])

    def test_nested_approval_wait_suspends_tool_deadline_and_resumes(self):
        self.manager.limits["tool_timeout"] = 0.2
        with patch("local_agent.studio.manager.worker_main", lifecycle_worker):
            task, state = self.start(objective="nested_approvals")
        self.wait_until(lambda: len(self.manager.pending()) == 2)
        with self.manager.lock:
            state["task_deadline"] = time.monotonic() + 0.2
        time.sleep(0.35)
        self.assertEqual(self.manager.store.tasks()[0]["status"], "waiting")
        self.manager.approve(task, "inner", True)
        self.assertEqual(self.manager.store.tasks()[0]["status"], "waiting")
        time.sleep(0.25)
        self.assertEqual(len(self.manager.pending()), 1)
        self.manager.approve(task, "outer", True)
        self.settled(task, state, "reported")
        self.assertFalse(any(e["kind"] == "heartbeat" for e in self.manager.store.events()))

    def test_expired_approval_is_blocked_not_a_tool_timeout(self):
        self.manager.limits.update(tool_timeout=0.15, approval_timeout=0.4)
        task, state = self.start()
        self.wait_until(lambda: bool(self.manager.pending()))
        result = self.settled(task, state, "blocked")
        self.assertNotIn("deadline exceeded", result.get("report", ""))
        self.assertFalse((self.policy.root / "review.txt").exists())

    def test_late_approval_click_cannot_remove_the_expiry_boundary(self):
        self.manager.limits.update(tool_timeout=0.15, approval_timeout=0.4)
        task, state = self.start()
        self.wait_until(lambda: bool(self.manager.pending()))
        request = self.manager.pending()[0]
        with self.manager.lock:
            time.sleep(0.5)
            with self.assertRaises(ValueError):
                self.manager.approve(task, request["id"], True)
        self.settled(task, state, "blocked")
        self.assertFalse((self.policy.root / "review.txt").exists())

    def test_cancel_during_wait_clears_requests_and_emergency_stop_is_reusable(self):
        self.manager.limits["tool_timeout"] = 0.15
        task, state = self.start()
        self.wait_until(lambda: bool(self.manager.pending()))
        time.sleep(0.25)
        started = time.monotonic()
        self.manager.close()  # Emergency stop is not permanent backend shutdown.
        self.assertLess(time.monotonic() - started, 5)
        self.settled(task, state, "cancelled")
        self.assertFalse((self.policy.root / "review.txt").exists())
        self.assertFalse(self.manager.shutdown_requested.is_set())
        next_task, _ = self.start("chat", "Explicit request after emergency stop")
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.store.tasks()[0]["id"], next_task)
        self.assertEqual(self.manager.store.tasks()[0]["status"], "reported")

    def test_unavailable_completion_at_shutdown_recovers_as_interrupted(self):
        with patch.object(self.manager.store, "complete", side_effect=sqlite3.OperationalError("disk unavailable")):
            task, state = self.start("chat", "Respond before storage fails")
            self.wait_until(lambda: state.get("process_closed") and state.get("persist_error"))
            started = time.monotonic()
            self.manager.close(shutdown=True)
            self.assertLess(time.monotonic() - started, 5)
            self.assertFalse(self.manager.running)
        reopened = Manager(self.config)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.store.tasks()[0]["status"], "interrupted")
        events = [e for e in reopened.store.events() if e["kind"] == "result" and e["task"] == task]
        self.assertEqual(len(events), 1)
        self.assertEqual(len([m for m in reopened.store.messages(self.conversation) if m["role"] == "assistant"]), 1)
        self.assertEqual(len(self.requests), 1, "Restart recovery must not run the model again")
        self.thread_errors.assert_not_called()

    def hang_model(self):
        original = self.server.RequestHandlerClass
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        class HangingModel(original):
            def do_POST(self):
                entered.set()
                release.wait(8)
                try:
                    super().do_POST()
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server.RequestHandlerClass = HangingModel
        return entered, release

    def test_model_deadline_stops_hung_call_despite_real_heartbeats(self):
        entered, release = self.hang_model()
        self.manager.limits.update(model_timeout=1.8, heartbeat_timeout=1.4)
        task, state = self.start("chat", "Hang in the fixture model")
        self.assertTrue(entered.wait(3))
        result = self.settled(task, state, "failed")
        release.set()
        self.assertIn("model deadline", result["report"])

    def test_cancel_interrupts_an_actual_blocked_model_call(self):
        entered, release = self.hang_model()
        task, state = self.start("chat", "Block until cancelled")
        self.assertTrue(entered.wait(3))
        started = time.monotonic()
        self.manager.cancel(task)
        self.settled(task, state, "cancelled")
        self.assertLess(time.monotonic() - started, 5)
        release.set()

    def test_continuous_tokens_do_not_reset_model_deadline(self):
        original = self.server.RequestHandlerClass
        release = threading.Event()
        self.addCleanup(release.set)

        class EndlessStream(original):
            def do_POST(self):
                from .ollama_fixture import serve_metadata
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if serve_metadata(self, body):
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                try:
                    while not release.wait(0.05):
                        self.wfile.write(b'{"message":{"content":"streaming "}}\n')
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server.RequestHandlerClass = EndlessStream
        self.manager.limits["model_timeout"] = 1
        task, state = self.start("chat", "Stream until the phase budget expires")
        result = self.settled(task, state, "failed")
        release.set()
        self.assertIn("model deadline", result["report"])
        self.assertTrue(any(e["kind"] == "token" for e in self.manager.live_events))

    @unittest.skipUnless(os.name == "nt", "Windows owned process-tree boundary")
    def test_hung_command_after_approval_wait_kills_owned_descendant(self):
        import psutil
        self.config["commands"]["test"] = ["{python}", "-c",
            ("import os,pathlib,time; p=pathlib.Path('child-pid.tmp'); p.write_text(str(os.getpid())); "
             "p.replace('child-pid.txt'); time.sleep(30)")]
        self.manager.limits.update(tool_timeout=0.5, approval_timeout=5)
        task, state = self.start("test", "Run the fixture command")
        self.wait_until(lambda: bool(self.manager.pending()))
        time.sleep(1.1)  # Longer than the tool budget; heartbeat/approval wait must remain healthy.
        self.assertEqual(self.manager.store.tasks()[0]["status"], "waiting")
        request = self.manager.pending()[0]
        self.manager.approve(task, request["id"], True)
        pid_file = self.policy.root / "child-pid.txt"
        self.wait_until(pid_file.exists)
        pid = int(pid_file.read_text())
        result = self.settled(task, state, "failed")
        self.assertIn("tool deadline", result["report"])
        self.wait_until(lambda: not psutil.pid_exists(pid))

    def test_cancel_result_race_persists_one_outcome(self):
        task, state = self.start("chat", "Reply while cancellation races")
        gate = threading.Barrier(2)

        def cancel():
            gate.wait(3)
            self.manager.cancel(task)

        stopper = threading.Thread(target=cancel)
        stopper.start()
        gate.wait(3)
        stopper.join(3)
        self.wait_until(lambda: not self.manager.running)
        status = self.manager.store.tasks()[0]["status"]
        self.assertIn(status, {"reported", "cancelled"})
        self.settled(task, state, status)
        self.manager.cancel(task)  # Late duplicate cancellation must not add another outcome.
        self.settled(task, state, status)

    @unittest.skipUnless(os.name == "nt", "Windows Job Object fault injection")
    def test_job_and_process_stop_errors_use_kill_and_cleanup_retry(self):
        task, state = self.start()
        self.wait_until(lambda: bool(self.manager.pending()))
        original_close = state["job"].close
        attempts = []

        def close():
            attempts.append(True)
            if len(attempts) == 1:
                raise OSError("Injected Job close failure")
            return original_close()

        with patch.object(state["job"], "terminate", side_effect=OSError("Injected Job terminate failure")), \
                patch.object(state["job"], "close", side_effect=close), \
                patch.object(state["process"], "terminate", side_effect=OSError("Injected terminate failure")), \
                patch.object(state["process"], "kill", wraps=state["process"].kill) as kill:
            self.manager.cancel(task)
            self.settled(task, state, "cancelled")
            kill.assert_called()  # Repeated owned-handle kill attempts are safe cleanup, not tool replay.

    def test_pipe_close_failure_is_retried_before_releasing_ownership(self):
        task, state = self.start()
        self.wait_until(lambda: bool(self.manager.pending()))
        original = state["pipe"].close
        attempts = []

        def close():
            attempts.append(True)
            if len(attempts) == 1:
                raise OSError("Injected pipe close failure")
            original()

        with patch.object(state["pipe"], "close", side_effect=close):
            self.manager.cancel(task)
            self.settled(task, state, "cancelled")
        self.assertEqual(len(attempts), 2)
