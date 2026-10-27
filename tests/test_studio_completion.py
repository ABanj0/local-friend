"""Atomic completion with actual SQLite rollback, contention and restart recovery."""
import json
import sqlite3
import threading

from local_agent.studio.store import Store

from .support import WorkspaceTest


class StudioCompletionTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.store = Store(self.policy.state / "completion.sqlite3")
        self.conversation = self.store.conversation()

    def assert_outcome(self, task, status):
        row = next(t for t in self.store.tasks() if t["id"] == task)
        events = [e for e in self.store.events() if e["task"] == task and e["kind"] == "result"]
        self.assertEqual(row["status"], status)
        self.assertEqual(len(events), 1)
        self.assertEqual(json.loads(row["result"]), events[0]["payload"])
        return events[0]

    def test_completion_is_atomic_idempotent_and_redacted(self):
        task = self.store.task(self.conversation, "chat", "fixture")
        payload = {"status": "reported", "report": "token=completion-canary", "metrics": {"generated_tokens": 7}}
        event = self.store.complete(task, payload)
        persisted = self.assert_outcome(task, "reported")
        self.assertEqual(event, {key: persisted[key] for key in event})
        self.assertIsNone(Store(self.store.path).complete(task, {"status": "cancelled", "report": "late stop"}))
        messages = self.store.messages(self.conversation)
        self.assertEqual(len(messages), 1)
        self.assertNotIn("completion-canary", messages[0]["content"])
        self.assertEqual(messages[0]["metrics"], payload["metrics"])
        self.assert_outcome(task, "reported")

    def test_sql_fault_rolls_back_task_message_event_and_goal(self):
        goal = self.store.create_goal(self.conversation, "Review the plan")
        for target in ("tasks", "messages", "events"):
            with self.subTest(target=target):
                task = self.store.task(self.conversation, "plan", "fixture", goal["id"])
                before = len(self.store.messages(self.conversation))
                operation = "UPDATE" if target == "tasks" else "INSERT"
                with self.store.connection() as db:
                    db.execute(f"CREATE TRIGGER fail_completion AFTER {operation} ON {target} "
                               "BEGIN SELECT RAISE(ABORT, 'injected terminal write failure'); END")
                with self.assertRaises(sqlite3.IntegrityError):
                    self.store.complete(task, {"status": "planned", "report": "Plan", "plan": {"steps": ["Inspect"]}})
                self.assertEqual(self.store.latest_task(self.conversation)["status"], "running")
                self.assertEqual(len(self.store.messages(self.conversation)), before)
                self.assertEqual(self.store.current_goal(self.conversation)["steps"], [])
                self.assertFalse(any(e["task"] == task for e in self.store.events()))
                with self.store.connection() as db:
                    db.execute("DROP TRIGGER fail_completion")
                self.store.complete(task, {"status": "failed", "report": "Stopped after storage fault"})
                self.assert_outcome(task, "failed")
        task = self.store.task(self.conversation, "plan", "fixture", goal["id"])
        self.store.complete(task, {"status": "planned", "report": "Plan", "plan": {"steps": ["Inspect"]}})
        self.assertEqual(self.store.current_goal(self.conversation)["steps"], [{"text": "Inspect", "done": False}])

    def test_concurrent_terminal_writers_have_one_winner(self):
        task = self.store.task(self.conversation, "chat", "fixture")
        gate = threading.Barrier(2)
        outcomes, errors = [], []

        def finish(status):
            try:
                store = Store(self.store.path)
                gate.wait(3)
                outcomes.append(store.complete(task, {"status": status, "report": status}))
            except Exception as exc:  # noqa: BLE001 -- surface thread failures in the test runner
                errors.append(exc)

        threads = [threading.Thread(target=finish, args=(s,)) for s in ("reported", "cancelled")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        winner = [outcome for outcome in outcomes if outcome]
        self.assertEqual(len(winner), 1)
        self.assert_outcome(task, winner[0]["payload"]["status"])
        self.assertEqual(len(self.store.messages(self.conversation)), 1)

    def test_restart_completes_running_and_waiting_without_replay(self):
        tasks = [self.store.task(self.conversation, "agent", "fixture") for _ in range(2)]
        self.store.waiting(tasks[1], True)
        self.store.event(tasks[1], "approval", {"secret": "private-approval"})
        reopened = Store(self.store.path)
        reopened.recover()
        reopened.recover()
        for task in tasks:
            self.assert_outcome(task, "interrupted")
        self.assertEqual(len(self.store.messages(self.conversation)), 2)
        self.assertNotIn("private-approval", json.dumps(self.store.events()))

    def test_invalid_terminal_status_does_not_change_state(self):
        task = self.store.task(self.conversation, "chat", "fixture")
        with self.assertRaises(ValueError):
            self.store.complete(task, {"status": "running", "report": "invalid"})
        self.assertEqual(self.store.tasks()[0]["status"], "running")
        self.assertEqual(self.store.messages(self.conversation), [])
        self.assertEqual(self.store.events(), [])
