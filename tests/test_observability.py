"""Content-free trace contracts, diagnostic privacy and real worker evidence."""
import copy
import json
import time
import uuid
from unittest.mock import patch

from local_agent.model import Ollama
from local_agent.observability import (
    MAX_SPANS,
    TOOLS,
    Trace,
    diagnostic,
    exception_status,
    numeric_metrics,
    tool_status,
    validate,
)
from local_agent.safety import Denied, Stopped
from local_agent.studio.store import Store
from local_agent.tools import Tools

from .studio_support import StudioAPIFixture, StudioProcessFixture
from .support import WorkspaceTest


class ObservabilityTests(WorkspaceTest):
    def trace(self):
        rows = []
        return Trace(uuid.uuid4().hex, self.config["model"], rows.append), rows

    def task(self, run_id, result=None, state="reported"):
        return {"id": run_id, "status": state, "result": result or {"observability": {"dropped_spans": 0}}}

    def test_tool_names_are_the_reviewed_registry_not_model_provided_labels(self):
        disabled = Tools(self.policy)
        self.addCleanup(disabled.close)
        self.assertEqual(TOOLS, set(disabled.registry) | {"unknown_tool", "mcp_project_read"})
        self.config["mcp"] = {"project_read": True}
        enabled = Tools(self.policy)
        self.addCleanup(enabled.close)
        self.assertEqual(TOOLS, set(enabled.registry) | {"unknown_tool"})
        trace, rows = self.trace()
        root = trace.start("run")
        with trace.span("tool", tool=["PRIVATE-CANARY"]):
            pass
        trace.finish(root, "reported")
        self.assertNotIn("PRIVATE-CANARY", json.dumps(rows))
        self.assertEqual(rows[1]["tool"], "unknown_tool")

    def test_ids_parentage_model_hashes_and_correlation_are_content_free(self):
        trace, rows = self.trace()
        root = trace.start("run")
        with trace.span("plan"), trace.span("model"):
            pass
        with trace.span("step", index=1), trace.span("tool", tool="write_file"):
            context = trace.context()
            with trace.span("approval") as wait:
                wait.status = "approved"
        trace.finish(root, "reported")
        states = {}
        for row in rows:
            validate(row, trace.run_id, states)
        self.assertEqual(context["run_id"], trace.run_id)
        self.assertIn(context["step_id"], states)
        self.assertIn(context["call_id"], states)
        self.assertEqual(len(states), 6)
        self.assertEqual(len(rows[0]["model_sha256"]), 64)
        self.assertNotIn(self.config["model"]["name"], json.dumps(rows))
        self.assertNotIn(self.config["model"]["url"], json.dumps(rows))

    def test_nested_approval_union_is_not_counted_twice(self):
        clock = [0, 0, 10, 20, 30, 50, 70, 90, 100]
        with patch("local_agent.observability.time.perf_counter_ns", side_effect=clock):
            trace, rows = self.trace()
            root = trace.start("run")
            with trace.span("tool", tool="browser_intervene"), trace.span("approval"), trace.span("approval"):
                pass
            trace.finish(root, "reported")
        result = diagnostic(self.task(trace.run_id), rows, [])
        timing = result["summary"]["latency_ms"]
        self.assertAlmostEqual(timing["approval_ms"], 50 / 1e6)
        self.assertAlmostEqual(timing["tool_active_ms"], 30 / 1e6)
        self.assertAlmostEqual(timing["other_ms"], 20 / 1e6)
        self.assertEqual(timing["worker_wall_ms"], 100 / 1e6)

    def test_error_taxonomy_excludes_raw_exception_messages(self):
        for error, expected in ((Denied("CANARY"), "denied"), (Stopped("CANARY"), "cancelled"),
                                (ValueError("CANARY"), "invalid_input"), (TimeoutError("CANARY"), "timeout"),
                                (OSError("CANARY"), "transport_error"), (RuntimeError("CANARY"), "error")):
            self.assertEqual(exception_status(error), expected)
        trace, rows = self.trace()
        root = trace.start("run")
        with self.assertRaises(Denied), trace.span("tool", tool="command"):
            raise Denied("password=EXCEPTION-CANARY")
        trace.finish(root, "blocked")
        self.assertNotIn("EXCEPTION-CANARY", json.dumps(rows))
        self.assertEqual(rows[-2]["status"], "denied")

    def test_reported_success_never_overrides_tool_or_verifier_failure(self):
        self.assertEqual(tool_status({"ok": True, "untrusted_data": {"exit_code": 1}}), "execution_failed")
        self.assertEqual(tool_status({"ok": True, "untrusted_data": {"verification": {"status": "failed"}}}), "verification_failed")
        self.assertEqual(tool_status({"ok": True, "untrusted_data": {"verification": {"status": "inconclusive"}}}), "inconclusive")
        self.assertEqual(tool_status({"ok": False, "error": "UNTRUSTED-CANARY"}), "error")
        trace, rows = self.trace()
        root = trace.start("run")
        with trace.span("tool", tool="command") as call:
            call.status = "verification_failed"
        trace.finish(root, "reported")
        result = diagnostic(self.task(trace.run_id, {"report": "Everything passed CANARY",
            "observability": {"dropped_spans": 0}}), rows, [])
        self.assertEqual(result["summary"]["tool_outcomes"], {"verification_failed": 1})
        self.assertEqual(result["summary"]["task_certification"], "not_assessed")
        self.assertNotIn("Everything passed", json.dumps(result))

    def test_interrupted_spans_have_unknown_duration_and_no_finished_status(self):
        trace, rows = self.trace()
        trace.start("run")
        trace.start("tool", tool="command")
        result = diagnostic(self.task(trace.run_id, state="cancelled"), rows, [])
        self.assertTrue(result["partial"])
        self.assertEqual(result["summary"]["incomplete_spans"], 2)
        self.assertTrue(all(span["observation_state"] == "interrupted" for span in result["spans"]))
        self.assertIsNone(result["summary"]["latency_ms"]["worker_wall_ms"])

    def test_budget_preserves_execution_and_explicitly_marks_missing_observations(self):
        with patch("local_agent.observability.MAX_SPANS", 4):
            trace, rows = self.trace()
            root = trace.start("run")
            for index in range(10):
                with trace.span("step", index=index + 1):
                    pass
            trace.finish(root, "reported")
        self.assertEqual(trace.dropped, 7)
        self.assertEqual(len(rows), 8)
        result = diagnostic(self.task(trace.run_id, {"observability": {"dropped_spans": trace.dropped}}), rows, [])
        self.assertTrue(result["partial"])
        self.assertEqual(result["dropped_spans"], 7)

    def test_malformed_records_fail_transactionally_without_leaking_fields(self):
        trace, rows = self.trace()
        trace.start("run")
        states = {}
        validate(rows[0], trace.run_id, states)
        before = copy.deepcopy(states)
        for changes in ({"phase": []}, {"status": "SECRET-CANARY"}, {"run_id": uuid.uuid4().hex},
                        {"id": "unknown"}, {"start_ns": True}, {"duration_ns": float("nan")},
                        {"prompt": "PRIVATE-CANARY"}):
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError):
                validate({**rows[0], **changes}, trace.run_id, states)
            self.assertEqual(states, before)

    def test_parent_cannot_finish_before_open_children_or_their_observed_end(self):
        trace, rows = self.trace()
        root = trace.start("run")
        child = trace.start("tool", tool="files")
        trace.finish(child)
        trace.finish(root)
        states = {}
        validate(rows[0], trace.run_id, states)
        validate(rows[1], trace.run_id, states)
        with self.assertRaises(ValueError):
            validate(rows[-1], trace.run_id, states)
        validate(rows[2], trace.run_id, states)
        with self.assertRaises(ValueError):
            validate({**rows[-1], "duration_ns": 0}, trace.run_id, states)

    def test_existing_native_metrics_are_reused_without_parsing_model_prose(self):
        model = Ollama(self.config["model"])
        model.record_usage({"done": True, "eval_count": 12, "eval_duration": 2_000_000_000})
        metrics = {**model.metrics(), "elapsed_seconds": 3, "scope": "task"}
        self.assertEqual(numeric_metrics(metrics)["tokens_per_second"], 6)
        for changes in ({"generated_tokens": True}, {"model_calls": "CANARY"}, {"tokens_per_second": float("nan")},
                        {"generated_tokens": 10**1000}):
            self.assertIsNone(numeric_metrics({**metrics, **changes}))

    def test_export_is_bounded_and_old_or_malformed_data_is_explicitly_incomplete(self):
        store = Store(self.policy.state / "diag.sqlite3")
        conversation = store.conversation("TITLE-PRIVATE-CANARY")
        task = store.task(conversation, "chat", "MODEL-PRIVATE-CANARY")
        store.finish(task, "reported", {"report": "PROMPT-PRIVATE-CANARY", "observability": []})
        store.event(task, "trace", {"argv": ["SEED-PRIVATE-CANARY"]})
        result = store.diagnostics(task)
        self.assertTrue(result["partial"])
        self.assertEqual(result["invalid_records"], 1)
        self.assertFalse(result["available"])
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))
        with store.connection() as db:
            db.executemany("INSERT INTO events(task,kind,payload,created) VALUES (?,?,?,?)",
                [(task, "trace", "{}", time.time())] * (MAX_SPANS * 2 + 3))
        result = store.diagnostics(task)
        self.assertEqual(result["invalid_records"], MAX_SPANS * 2)
        self.assertLess(len(json.dumps(result).encode()), 1024 * 1024)

    def test_export_excludes_exact_launch_credential_even_if_it_matches_an_identifier(self):
        store = Store(self.policy.state / "diag.sqlite3")
        conversation = store.conversation()
        task = store.task(conversation, "chat", "fixture")
        result = store.diagnostics(task, forbidden=(task,))
        self.assertNotIn(task, json.dumps(result))
        self.assertGreater(result["credential_values_removed"], 0)


class DiagnosticAPITests(StudioAPIFixture, WorkspaceTest):
    def test_authentication_missing_task_and_content_free_export(self):
        store = Store(self.policy.state / "studio.sqlite3")
        conversation = store.conversation("TITLE-PRIVATE-CANARY")
        task = store.task(conversation, "chat", "MODEL-PRIVATE-CANARY")
        store.finish(task, "reported", {"report": "TOKEN-PRIVATE-CANARY", "metrics": {"generated_tokens": "TOKEN-PRIVATE-CANARY"}})
        self.assertEqual(self.client.get(f"/tasks/{task}/diagnostics").status_code, 401)
        result = self.client.get(f"/tasks/{task}/diagnostics", headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("PRIVATE-CANARY", result.text)
        self.assertNotIn(self.headers["Authorization"].split()[1], result.text)
        self.assertIsNone(result.json()["inference"])
        self.assertEqual(self.client.get("/tasks/not-a-task/diagnostics", headers=self.headers).status_code, 404)

    def test_read_only_export_and_chat_deletion_preserve_existing_boundaries(self):
        store = Store(self.policy.state / "studio.sqlite3")
        conversation = store.conversation()
        task = store.task(conversation, "chat", "fixture")
        before = store.event_high_water()
        self.assertEqual(self.client.get(f"/tasks/{task}/diagnostics", headers=self.headers).status_code, 200)
        self.assertEqual(store.event_high_water(), before)
        store.delete_conversation(conversation)
        self.assertEqual(self.client.get(f"/tasks/{task}/diagnostics", headers=self.headers).status_code, 404)


class DiagnosticProcessTests(StudioProcessFixture, WorkspaceTest):
    def test_real_agent_correlates_model_step_tool_approval_and_verifier_without_content(self):
        task = self.manager.start(self.conversation, "OBJECTIVE-PRIVATE-CANARY", "agent", "fixture")
        self.wait_until(lambda: self.manager.pending())
        approval = self.manager.pending()[0]
        self.assertEqual(approval["correlation"]["run_id"], task)
        self.assertIsNotNone(approval["correlation"]["call_id"])
        self.manager.approve(task, approval["id"], True)
        self.wait_until(lambda: not self.manager.running)
        result = self.manager.store.diagnostics(task)
        self.assertFalse(result["partial"], result)
        self.assertEqual(result["inference"]["generated_tokens"], 30)
        self.assertEqual({span["kind"] for span in result["spans"]}, {"run", "plan", "step", "model", "tool", "approval", "cleanup"})
        tool = next(span for span in result["spans"] if span["kind"] == "tool")
        self.assertEqual(tool["verification_ids"], [result["verifications"][0]["id"]])
        self.assertEqual(tool["id"], approval["correlation"]["call_id"])
        self.assertNotIn("PRIVATE-CANARY", json.dumps(result))
        self.assertNotIn("review.txt", json.dumps(result))
        reopened = Store(self.policy.state / "studio.sqlite3")
        self.assertEqual(reopened.diagnostics(task), result)

    def test_failed_tests_stay_failed_in_taxonomy_and_counters_are_not_invented(self):
        (self.policy.root / "test_fail.py").write_text("import unittest\nclass Failed(unittest.TestCase):\n"
            " def test_failure(self):self.assertEqual(1,2)\n", encoding="utf-8")
        task = self.manager.start(self.conversation, "Run tests", "test", "fixture", profile="coding")
        self.wait_until(lambda: self.manager.pending())
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: not self.manager.running)
        result = self.manager.store.diagnostics(task)
        self.assertEqual(result["summary"]["tool_outcomes"], {"verification_failed": 1})
        self.assertEqual(result["verifications"][0]["status"], "failed")
        self.assertIsNone(result["inference"])
        self.assertEqual(result["summary"]["task_certification"], "not_assessed")

    def test_cancelled_approval_wait_is_interrupted_not_a_completed_tool(self):
        task = self.manager.start(self.conversation, "Write a file", "agent", "fixture")
        self.wait_until(lambda: self.manager.pending())
        self.manager.cancel(task)
        self.wait_until(lambda: not self.manager.running)
        result = self.manager.store.diagnostics(task)
        self.assertTrue(result["partial"])
        self.assertGreaterEqual(result["summary"]["incomplete_spans"], 3)
        self.assertTrue(any(span["observation_state"] == "interrupted" for span in result["spans"]))
        self.assertFalse(result["verifications"])
