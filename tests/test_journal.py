"""Durability and recovery against isolated SQLite stores and real spawned workers."""
import copy
import hashlib
import json
import os
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from local_agent.observability import TOOLS, Trace
from local_agent.studio import journal
from local_agent.studio.store import Store

from .studio_support import StudioAPIFixture, StudioProcessFixture
from .support import WorkspaceTest


def crash_worker(pipe, config, mode, objective, history, current_message=None):
    """Test-only spawn target; production has no crash switch or replay path."""
    from local_agent.studio.worker import worker_main
    from local_agent.tools import Tools

    start, finish, execute = Trace.start, Trace.finish, Tools.execute

    def crashing_start(self, kind, **kwargs):
        span = start(self, kind, **kwargs)
        if objective == "before-intent" and kind == "tool":
            os._exit(31)
        return span

    def crashing_execute(self, name, arguments):
        if objective == "during-execution":
            os._exit(32)
        result = execute(self, name, arguments)
        if objective == "after-effect":
            os._exit(33)
        return result

    def crashing_finish(self, span, status=None):
        if objective == "after-result" and span.record and span.record["kind"] == "tool":
            os._exit(34)
        return finish(self, span, status)

    with patch.object(Trace, "start", crashing_start), patch.object(Trace, "finish", crashing_finish), patch.object(Tools, "execute", crashing_execute):
        worker_main(pipe, config, mode, objective, history, current_message)


class JournalStoreFixture:
    def setUp(self):
        super().setUp()
        self.store = Store(self.policy.state / "journal.db")
        self.conversation = self.store.conversation()
        self.task = self.store.task(self.conversation, "agent", "fixture", project=".", scope_key=journal.scope_key(self.policy.root))
        records = []
        trace = Trace(self.task, self.config["model"], records.append)
        trace.start("run")
        span = trace.start("step", index=1)
        self.step_record = records[-1]
        self.store.record_step(self.task, self.step_record)
        self.operation = {"version": 1, "id": uuid.uuid4().hex, "step": span.record["id"],
                          "tool": "write_file", "effect": "filesystem", "arguments_sha256": journal.digest({"path": "out.txt", "text": "private body"}),
                          "preconditions": journal.Preconditions(self.policy, "write_file", {"path": "out.txt", "text": "private body"}).public}


class JournalStoreTests(JournalStoreFixture, WorkspaceTest):
    def test_intent_result_and_events_are_atomic_and_result_idempotent(self):
        event = self.store.operation_intent(self.task, self.operation)
        self.assertEqual(event["kind"], "operation_intent")
        with self.assertRaises(ValueError):
            self.store.operation_intent(self.task, self.operation)
        result = {"version": 1, "id": self.operation["id"], "outcome": "observed", "verification_ids": []}
        self.store.operation_result(self.task, result)
        self.assertIsNone(self.store.operation_result(self.task, result))
        self.assertEqual(len([e for e in self.store.events() if e["kind"] == "operation_result"]), 1)
        self.assertNotIn("private body", json.dumps(self.store.journal(self.task)))
        self.assertEqual(self.store.journal(self.task)["operations"][0]["state"], "completed")
        with self.assertRaises(ValueError):
            self.store.operation_result(self.task, {**result, "outcome": "denied"})
        with patch.object(self.store, "_journal_event", side_effect=RuntimeError("failed event commit")), self.assertRaises(RuntimeError):
            self.store.operation_intent(self.task, {**self.operation, "id": uuid.uuid4().hex})
        self.assertEqual(len(self.store.journal(self.task)["operations"]), 1)

    def test_cross_task_and_missing_verifier_references_cannot_complete(self):
        self.store.operation_intent(self.task, self.operation)
        other = self.store.task(self.conversation, "agent", "fixture")
        result = {"version": 1, "id": self.operation["id"], "outcome": "observed", "verification_ids": []}
        with self.assertRaises(ValueError):
            self.store.operation_result(other, result)
        with self.assertRaises(ValueError):
            self.store.operation_result(self.task, {**result, "verification_ids": [uuid.uuid4().hex]})
        self.assertEqual(self.store.journal(self.task)["operations"][0]["state"], "intent")

    def test_restart_reconciles_unknown_effect_and_never_replays_or_accepts_late_result(self):
        self.store.operation_intent(self.task, self.operation)
        reopened = Store(self.store.path)
        reopened.recover()
        snapshot = reopened.journal(self.task)
        self.assertEqual(snapshot["steps"][0]["state"], "unknown")
        self.assertEqual(snapshot["operations"][0]["state"], "unknown")
        self.assertFalse((self.policy.root / "out.txt").exists())
        self.assertFalse(snapshot["replay_supported"])
        self.assertIsNone(reopened.operation_result(self.task, {"version": 1, "id": self.operation["id"], "outcome": "observed", "verification_ids": []}))
        self.assertEqual(reopened.journal(self.task), snapshot)

    def test_read_only_intent_is_interrupted_and_deletion_cascades(self):
        self.store.operation_intent(self.task, {**self.operation, "tool": "read_file", "effect": "read", "preconditions": []})
        self.store.recover()
        self.assertEqual(self.store.journal(self.task)["operations"][0]["state"], "interrupted")
        self.store.delete_conversation(self.conversation)
        with self.store.connection() as db:
            for table in ("operations", "execution_steps"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)

    def test_inspection_compares_current_bytes_but_does_not_resolve_unknown(self):
        self.store.operation_intent(self.task, self.operation)
        self.store.recover()
        target = self.policy.root / "out.txt"
        target.write_text("private body", encoding="utf-8")
        before = self.store.journal(self.task)
        result = journal.inspect_operation(self.store, self.config, self.task, self.operation["id"])
        self.assertTrue(result["artifacts"][0]["matches_proposed"])
        self.assertFalse(result["artifacts"][0]["matches_before"])
        self.assertNotIn("private body", json.dumps(result))
        self.assertEqual(self.store.journal(self.task), before)
        target.unlink()
        result = journal.inspect_operation(self.store, self.config, self.task, self.operation["id"])
        self.assertTrue(result["artifacts"][0]["matches_before"])

    def test_inspection_requires_current_scope_and_rejects_credentials_links_and_stop(self):
        self.store.operation_intent(self.task, self.operation)
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "out.txt").write_text("private body")
        config = copy.deepcopy(self.config)
        config["paths"]["workspace"] = str(outside)
        result = journal.inspect_operation(self.store, config, self.task, self.operation["id"])
        self.assertEqual(result["artifacts"][0]["current"], "unavailable")
        config["paths"]["workspace"] = str(outside / "missing-work")
        config["paths"]["state"] = str(outside / "missing-state")
        result = journal.inspect_operation(self.store, config, self.task, self.operation["id"])
        self.assertEqual(result["artifacts"][0]["current"], "unavailable")
        self.assertFalse((outside / "missing-work").exists())
        self.assertFalse((outside / "missing-state").exists())
        for name in (".env", "alias.txt"):
            with self.subTest(path=name):
                source = outside / "out.txt"
                target = self.policy.root / name
                if name == "alias.txt":
                    os.link(source, target)
                else:
                    target.write_text("credential")
                artifact = {**self.operation["preconditions"][0], "path": name,
                            "resource_sha256": hashlib.sha256(name.encode()).hexdigest()}
                with self.store.connection() as db:
                    db.execute("UPDATE operations SET preconditions=?", (json.dumps([artifact]),))
                result = journal.inspect_operation(self.store, self.config, self.task, self.operation["id"])
                self.assertEqual(result["artifacts"][0]["current"], "unavailable")
        with self.store.connection() as db:
            db.execute("UPDATE operations SET preconditions=?", (json.dumps(self.operation["preconditions"]),))
        (self.policy.state / "STOP").touch()
        result = journal.inspect_operation(self.store, self.config, self.task, self.operation["id"])
        self.assertEqual(result["artifacts"][0]["current"], "unavailable")

    def test_preconditions_are_versions_not_authority_and_changed_input_is_detected(self):
        target = self.policy.root / "out.txt"
        target.write_text("old")
        before = journal.Preconditions(self.policy, "write_file", {"path": "out.txt", "text": "new"})
        self.assertTrue(before.unchanged())
        target.write_text("changed")
        self.assertFalse(before.unchanged())
        self.assertEqual(before.public[0]["sha256"], hashlib.sha256(b"old").hexdigest())
        denied = journal.Preconditions(self.policy, "write_file", {"path": "../outside", "text": "secret"})
        self.assertEqual(denied.public, [])

    def test_malformed_or_oversized_persisted_records_are_partial_not_exposed(self):
        self.store.operation_intent(self.task, self.operation)
        for column, value in (("preconditions", "secret" * 9000), ("ordinal", 9000), ("updated", "secret"), ("outcome", "forged")):
            with self.subTest(column=column):
                with self.store.connection() as db:
                    old = db.execute(f"SELECT {column} FROM operations").fetchone()[0]
                    db.execute(f"UPDATE operations SET {column}=?", (value,))
                snapshot = self.store.journal(self.task)
                self.assertTrue(snapshot["partial"])
                self.assertEqual(snapshot["operations"], [])
                with self.store.connection() as db:
                    db.execute(f"UPDATE operations SET {column}=?", (old,))

    def test_effect_classes_cover_registry_and_validation_rejects_raw_bodies(self):
        self.assertEqual(journal.effect("git", {"action": "diff"}), "read")
        self.assertEqual(journal.effect("git", {"action": "commit"}), "git")
        for tool in TOOLS:
            self.assertIn(journal.effect(tool, {}), journal.EFFECTS)
        for changes in ({"approval": "approved"}, {"arguments": {"text": "secret"}}, {"id": "wrong"}, {"preconditions": [{}]}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, TypeError)):
                journal.intent({**self.operation, **changes})


class JournalProcessTests(StudioProcessFixture, WorkspaceTest):
    def run_crash(self, phase):
        with patch("local_agent.studio.manager.worker_main", crash_worker):
            task = self.manager.start(self.conversation, phase, "agent", "fixture")
        if phase in {"after-effect", "after-result"}:
            self.wait_until(lambda: bool(self.manager.pending()))
            self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: not self.manager.running)
        snapshot = self.manager.store.journal(task)
        self.assertEqual(self.manager.store.tasks()[0]["status"], "failed")
        self.assertEqual(len(snapshot["steps"]), 1)
        self.assertNotEqual(snapshot["steps"][0]["state"], "running")
        self.assertEqual((self.policy.root / "review.txt").exists(), phase in {"after-effect", "after-result"})
        self.assertFalse(self.manager.pending())
        reopened = Store(self.manager.store.path)
        reopened.recover()
        self.assertEqual(reopened.journal(task), snapshot)
        return task, snapshot

    def test_crash_before_intent_has_interrupted_step_and_zero_operations(self):
        _, snapshot = self.run_crash("before-intent")
        self.assertEqual(snapshot["operations"], [])
        self.assertEqual(snapshot["steps"][0]["state"], "interrupted")

    def test_crash_during_execution_has_unknown_effect(self):
        _, snapshot = self.run_crash("during-execution")
        self.assertEqual(snapshot["operations"][0]["state"], "unknown")
        self.assertEqual(snapshot["steps"][0]["state"], "unknown")

    def test_crash_after_effect_can_inspect_but_never_replay(self):
        task, snapshot = self.run_crash("after-effect")
        op = snapshot["operations"][0]
        self.assertEqual(op["state"], "unknown")
        result = journal.inspect_operation(self.manager.store, self.config, task, op["id"])
        self.assertTrue(result["artifacts"][0]["matches_proposed"])
        self.assertEqual(len(self.requests), 2)

    def test_crash_after_result_preserves_completed_result_and_verifier_reference(self):
        _, snapshot = self.run_crash("after-result")
        op = snapshot["operations"][0]
        self.assertEqual(op["state"], "completed")
        self.assertEqual(op["outcome"], "observed")
        self.assertEqual(len(op["verification_ids"]), 1)
        self.assertEqual(snapshot["steps"][0]["state"], "interrupted")

    def test_failed_intent_commit_prevents_dispatch_and_approval(self):
        with patch.object(self.manager.store, "operation_intent", side_effect=OSError("storage unavailable")):
            task = self.manager.start(self.conversation, "write", "agent", "fixture")
            self.wait_until(lambda: not self.manager.running)
        self.assertFalse((self.policy.root / "review.txt").exists())
        self.assertEqual(self.manager.store.journal(task)["operations"], [])
        self.assertFalse(any(e["kind"] == "approval" for e in self.manager.store.events()))

    def test_mismatched_intent_acknowledgement_stops_before_side_effect(self):
        import multiprocessing
        from multiprocessing.connection import Connection

        # Windows uses PipeConnection; select the actual connection class.
        ends = multiprocessing.Pipe()
        connection_type = type(ends[0])
        for end in ends:
            end.close()
        original = Connection.send

        def altered(connection, message):
            if isinstance(message, dict) and message.get("journal_ack") == "intent":
                message = {**message, "id": "0" * 32}
            return original(connection, message)

        with patch.object(connection_type, "send", altered):
            task = self.manager.start(self.conversation, "write", "agent", "fixture")
            self.wait_until(lambda: not self.manager.running)
        self.assertFalse((self.policy.root / "review.txt").exists())
        self.assertEqual(self.manager.store.journal(task)["operations"][0]["state"], "unknown")
        self.assertFalse(self.manager.pending())

    def test_result_commit_failure_stops_next_model_call_and_preserves_unknown(self):
        with patch.object(self.manager.store, "operation_result", side_effect=OSError("storage unavailable")):
            task = self.manager.start(self.conversation, "write", "agent", "fixture")
            self.wait_until(lambda: bool(self.manager.pending()))
            self.manager.approve(task, self.manager.pending()[0]["id"], True)
            self.wait_until(lambda: not self.manager.running)
        self.assertTrue((self.policy.root / "review.txt").exists())
        self.assertEqual(self.manager.store.journal(task)["operations"][0]["state"], "unknown")
        self.assertEqual(len(self.requests), 2)

    def test_failure_after_result_transaction_preserves_evidence_without_next_dispatch(self):
        original = self.manager.store.operation_result

        def after_commit(*args):
            original(*args)
            raise OSError("lost acknowledgement after committed result")

        with patch.object(self.manager.store, "operation_result", side_effect=after_commit):
            task = self.manager.start(self.conversation, "write", "agent", "fixture")
            self.wait_until(lambda: bool(self.manager.pending()))
            self.manager.approve(task, self.manager.pending()[0]["id"], True)
            self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.store.journal(task)["operations"][0]["state"], "completed")
        self.assertEqual(len(self.requests), 2)

    def test_uncommitted_result_is_not_acknowledged_as_durable(self):
        with patch.object(self.manager.store, "operation_result", return_value=None):
            task = self.manager.start(self.conversation, "write", "agent", "fixture")
            self.wait_until(lambda: bool(self.manager.pending()))
            self.manager.approve(task, self.manager.pending()[0]["id"], True)
            self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.store.journal(task)["operations"][0]["state"], "unknown")
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.manager.store.tasks()[0]["status"], "failed")

    def test_file_changed_during_intent_commit_is_not_overwritten_or_approved(self):
        original = self.manager.store.operation_intent

        def changed(*args):
            event = original(*args)
            (self.policy.root / "review.txt").write_text("user changed file")
            return event

        with patch.object(self.manager.store, "operation_intent", side_effect=changed):
            task = self.manager.start(self.conversation, "write", "agent", "fixture")
            self.wait_until(lambda: not self.manager.running)
        self.assertEqual((self.policy.root / "review.txt").read_text(), "user changed file")
        self.assertEqual(self.manager.store.journal(task)["operations"][0]["outcome"], "denied")
        self.assertFalse(any(e["kind"] == "approval" for e in self.manager.store.events()))

    def test_denial_is_durable_but_approvals_remain_transient_and_new_run_needs_approval(self):
        task = self.manager.start(self.conversation, "write", "agent", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        request = self.manager.pending()[0]
        self.manager.approve(task, request["id"], False)
        self.wait_until(lambda: not self.manager.running)
        op = self.manager.store.journal(task)["operations"][0]
        self.assertEqual(op["outcome"], "denied")
        approvals = [e for e in self.manager.store.events() if e["kind"] == "approval"]
        self.assertEqual([e["payload"] for e in approvals], [{"transient": True}])
        new = self.manager.start(self.conversation, "write again", "agent", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.assertNotEqual(self.manager.pending()[0]["id"], request["id"])
        self.assertNotEqual(self.manager.store.journal(new)["operations"][0]["id"], op["id"])
        self.assertEqual(self.manager.store.journal(new)["operations"][0]["arguments_sha256"], op["arguments_sha256"])
        self.assertFalse((self.policy.root / "review.txt").exists())
        self.manager.cancel(new)


class JournalAPITests(StudioAPIFixture, WorkspaceTest):
    def test_journal_and_inspection_are_authenticated_and_unknown_ids_are_not_found(self):
        for path in (f"/tasks/{'a'*32}/journal", f"/tasks/{'a'*32}/journal/{'b'*32}/inspect"):
            self.assertEqual(self.client.get(path).status_code, 401)
            self.assertEqual(self.client.get(path, headers=self.headers).status_code, 404)

    def test_authenticated_inspection_does_not_change_state_and_rejects_other_methods(self):
        store = self.client.app.state.manager.store
        conversation = store.conversation()
        task = store.task(conversation, "agent", "fixture", project=".", scope_key=journal.scope_key(self.policy.root))
        records = []
        trace = Trace(task, self.config["model"], records.append)
        trace.start("run")
        step = trace.start("step", index=1)
        store.record_step(task, records[-1])
        operation = {"version": 1, "id": uuid.uuid4().hex, "step": step.record["id"], "tool": "write_file",
                     "effect": "filesystem", "arguments_sha256": journal.digest({}), "preconditions":
                     journal.Preconditions(self.policy, "write_file", {"path": "api.txt", "text": "body"}).public}
        store.operation_intent(task, operation)
        store.recover()
        before = self.client.get(f"/tasks/{task}/journal", headers=self.headers).json()
        path = f"/tasks/{task}/journal/{operation['id']}/inspect"
        inspected = self.client.get(path, headers=self.headers)
        self.assertEqual(inspected.status_code, 200)
        self.assertEqual(inspected.json()["artifacts"][0]["current"], "missing")
        self.assertEqual(self.client.get(f"/tasks/{task}/journal", headers=self.headers).json(), before)
        self.assertEqual(self.client.post(path, headers=self.headers).status_code, 405)
        self.assertFalse((self.policy.root / "api.txt").exists())


class JournalLiveModelTests(WorkspaceTest):
    @unittest.skipUnless(os.getenv("LOCAL_AGENT_MODEL_TEST") == "1", "Actual Ollama Studio journal acceptance is opt-in")
    def test_actual_model_workflow_has_committed_operations_and_artifact_evidence(self):
        from local_agent.benchmark import ensure_idle
        from local_agent.config import load
        from local_agent.studio.manager import Manager

        ensure_idle(load())
        manager = Manager(self.config)
        self.addCleanup(manager.close)
        conversation = manager.store.conversation()
        task = manager.start(conversation, "Create journal-live.txt containing exactly JOURNAL-LOCAL-917. "
                             "Read the file to verify the content, then report the result. Do not run commands or use other tools.",
                             "coding", self.config["model"]["name"], profile="coding")
        deadline = time.monotonic() + 120
        while manager.running and time.monotonic() < deadline:
            for request in manager.pending():
                # Disposable exact artifact only; no command/browser/desktop grants.
                details = request.get("details", {})
                allowed = (request.get("action") == "create_file" and details.get("path") == "journal-live.txt"
                           and details.get("proposed_content") == "JOURNAL-LOCAL-917")
                manager.approve(task, request["id"], allowed)
            time.sleep(.05)
        self.assertFalse(manager.running, "Actual-model task timed out")
        self.assertEqual((self.policy.root / "journal-live.txt").read_bytes(), b"JOURNAL-LOCAL-917")
        snapshot = manager.store.journal(task)
        self.assertFalse(snapshot["partial"])
        self.assertTrue(snapshot["operations"])
        self.assertTrue(all(op["state"] == "completed" for op in snapshot["operations"]))
        self.assertEqual(manager.store.tasks()[0]["status"], "reported")
        self.assertTrue(any(op["tool"] == "read_file" and op["outcome"] == "observed" for op in snapshot["operations"]))
        writes = [op for op in snapshot["operations"] if op["tool"] == "write_file"]
        self.assertTrue(writes and writes[0]["verification_ids"])
        print("Actual-model journal:", json.dumps({"steps": len(snapshot["steps"]), "operations": len(snapshot["operations"]),
              "tool_outcomes": [[op["tool"], op["outcome"]] for op in snapshot["operations"]],
              "task_status": manager.store.tasks()[0]["status"]}), flush=True)
