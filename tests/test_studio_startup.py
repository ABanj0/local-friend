"""Startup fault injection with real gated workers and owned resource checks."""
import json
import multiprocessing
import os
import threading
import time
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from . import studio_support as fixtures
from .support import WorkspaceTest


class StudioStartupTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.processes, self.connections, self.monitors, self.exitcodes = [], [], [], []
        self.close_counts = {}
        self.addCleanup(self.release_test_resources)

    def release_test_resources(self):
        # Keep a failing regression safe even against an implementation that leaks.
        with self.manager.lock:
            for state in self.manager.running.values():
                state["done"] = True
                if state["job"]:
                    state["job"].close()
            self.manager.running.clear()
        for proc in self.processes:
            try:
                if proc.pid is not None:
                    if proc.is_alive():
                        proc.kill()
                    proc.join(5)
                proc.close()
            except ValueError:
                pass  # Already closed by startup compensation.
        for connection in self.connections:
            connection.close()
        for monitor in self.monitors:
            if monitor.ident is not None:
                monitor.join(2)

    def fail_start(self, phase):
        context = multiprocessing.get_context("spawn")
        factory = Mock(wraps=context)
        real_thread = threading.Thread
        original_start = multiprocessing.process.BaseProcess.start
        original_close = multiprocessing.process.BaseProcess.close

        def create_pipe():
            if phase == "pipe":
                raise OSError("Injected pipe failure")
            parent, child = context.Pipe()
            self.connections.extend((parent, child))
            if phase == "send":
                parent.send = Mock(side_effect=BrokenPipeError("Injected start send failure"))
            return parent, child

        def create_process(*args, **kwargs):
            if phase == "process_constructor":
                raise OSError("Injected process constructor failure")
            proc = context.Process(*args, **kwargs)
            self.processes.append(proc)
            return proc

        # Patch class methods, not instance attributes: spawn pickles the Process object.
        def start(proc):
            if proc in self.processes and phase == "spawn":
                raise OSError("Injected spawn failure token=startup-canary")
            original_start(proc)
            if proc in self.processes and phase == "partial_spawn":
                raise OSError("Injected failure after process creation")

        def close(proc):
            if proc in self.processes:
                self.exitcodes.append(proc.exitcode)
                self.close_counts[id(proc)] = self.close_counts.get(id(proc), 0) + 1
            original_close(proc)

        def create_thread(*args, **kwargs):
            thread = real_thread(*args, **kwargs)
            self.monitors.append(thread)
            if phase == "monitor":
                thread.start = Mock(side_effect=RuntimeError("Injected monitor start failure"))
            return thread

        factory.Pipe.side_effect = create_pipe
        factory.Process.side_effect = create_process
        with ExitStack() as patches:
            patches.enter_context(patch("local_agent.studio.manager.multiprocessing.get_context",
                                        return_value=factory))
            patches.enter_context(patch("local_agent.studio.manager.threading.Thread", side_effect=create_thread))
            patches.enter_context(patch("multiprocessing.process.BaseProcess.start", autospec=True, side_effect=start))
            patches.enter_context(patch("multiprocessing.process.BaseProcess.close", autospec=True, side_effect=close))
            thread_errors = patches.enter_context(patch("threading.excepthook"))
            if phase == "job":
                patches.enter_context(patch("local_agent.windows_job.WindowsJob",
                                            side_effect=OSError("Injected Job Object failure")))
            if phase == "message":
                patches.enter_context(patch.object(self.manager.store, "message",
                                                   side_effect=ValueError("Injected message failure")))
            if phase == "started_event":
                original_emit = self.manager.emit

                def emit(task, kind, payload):
                    if kind == "started":
                        raise OSError("Injected started event failure")
                    return original_emit(task, kind, payload)

                patches.enter_context(patch.object(self.manager, "emit", side_effect=emit))
            started = time.monotonic()
            with self.assertRaises(OSError) as raised:
                self.manager.start(self.conversation, "Do not execute during failed startup", "agent", "fixture")
            self.assertLess(time.monotonic() - started, 5)
            self.assertIn("Task startup failed", str(raised.exception))
            self.assertNotIn("startup-canary", str(raised.exception))
            expected_phase = {"job": "establishing the cancellation boundary", "send": "releasing the worker",
                              "monitor": "starting the monitor", "started_event": "publishing startup"}
            if phase in expected_phase:
                self.assertIn(expected_phase[phase], str(raised.exception))
            for monitor in self.monitors:
                if monitor.ident is not None:
                    monitor.join(2)
                self.assertFalse(monitor.is_alive())
            thread_errors.assert_not_called()
        self.assertFalse(self.manager.running)
        capture_root = self.policy.state / "captures"
        self.assertFalse([path for path in capture_root.iterdir() if path.is_dir()],
                         "Failed startup must release screenshot ownership")
        self.assertEqual(self.manager.pending(), [])
        task = self.manager.store.tasks()[0]
        self.assertEqual(task["status"], "failed")
        self.assertNotIn("startup-canary", task["result"])
        terminal = [e for e in self.manager.store.events() if e["kind"] == "result"]
        self.assertEqual(len(terminal), 1)
        self.assertEqual(terminal[0]["payload"], json.loads(task["result"]))
        self.assertEqual(self.requests, [], "Failed startup must not release the worker's execution gate")
        self.assertFalse((self.policy.root / "review.txt").exists())
        for connection in self.connections:
            self.assertTrue(connection.closed)
        for proc in self.processes:
            self.assertEqual(self.close_counts[id(proc)], 1)
            with self.assertRaises(ValueError):
                proc.is_alive()  # Closed process handles, not just a removed manager entry.
        if phase in {"partial_spawn", "job", "send", "monitor", "started_event"}:
            self.assertTrue(self.exitcodes)
            self.assertTrue(all(code is not None for code in self.exitcodes))

    def test_spawn_failure_is_terminal_and_a_fresh_task_can_run(self):
        self.fail_start("spawn")
        self.manager.start(self.conversation, "Respond normally after the failed task", "chat", "fixture")
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.store.tasks()[0]["status"], "reported")
        self.assertEqual(self.manager.store.messages(self.conversation)[-1]["content"], "hello world")

    def test_partial_spawn_failure_closes_the_created_process(self):
        self.fail_start("partial_spawn")

    @unittest.skipUnless(os.name == "nt", "Windows Job Object startup boundary")
    def test_job_failure_never_releases_worker(self):
        self.fail_start("job")

    def test_initial_send_failure_stops_worker_and_monitor(self):
        self.fail_start("send")

    def test_monitor_start_failure_never_releases_worker(self):
        self.fail_start("monitor")

    def test_pipe_failure_marks_task_failed(self):
        self.fail_start("pipe")

    def test_process_constructor_failure_closes_both_pipe_ends(self):
        self.fail_start("process_constructor")

    def test_message_failure_does_not_leave_a_running_task(self):
        self.fail_start("message")

    def test_started_event_failure_never_releases_worker(self):
        self.fail_start("started_event")


@unittest.skipUnless(fixtures.HAS_API, "Desktop API dependencies not installed")
class StudioStartupAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_startup_failure_is_redacted_and_visible_through_api(self):
        manager = self.client.app.state.manager
        conversation = manager.store.conversation()
        from .ollama_fixture import metadata_response
        with patch("local_agent.studio.api.Ollama.request", side_effect=metadata_response), \
                patch("multiprocessing.process.BaseProcess.start",
                      side_effect=OSError("Injected spawn failure token=api-startup-canary")):
            response = self.client.post("/tasks", headers=self.headers, json={
                "conversation": conversation, "objective": "Read files", "mode": "agent", "model": "fixture"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("Task startup failed", response.json()["detail"])
        self.assertNotIn("api-startup-canary", response.text)
        tasks = self.client.get("/tasks", headers=self.headers).json()
        self.assertEqual(tasks["tasks"][0]["status"], "failed")
        self.assertEqual(tasks["approvals"], [])
        self.assertNotIn("api-startup-canary", json.dumps(tasks))
        self.assertFalse(manager.running)
