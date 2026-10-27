"""Honest success/failure oracles plus an opt-in real local-model coding workflow."""
import copy
import hashlib
import json
import os
import shutil
import sys

from local_agent.agent import Agent
from local_agent.benchmark import ensure_idle
from local_agent.model import Ollama
from local_agent.verification import RUNNER

from .coding_acceptance import BROKEN_COUNTER, OBJECTIVE, CodingScenario, assert_test_run
from .support import WorkspaceTest


class CodingAcceptanceTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        self.scenario = CodingScenario(self)

    def exercise_fixture(self, extra_tests=True):
        # Deterministic verifier coverage, explicitly not evidence of autonomous debugging.
        tools = self.scenario.tools
        tools.execute("read_file", {"path": "counter.py"})
        tools.execute("command", {"name": "test"})
        tools.execute("write_file", {"path": "counter.py", "text":
                      BROKEN_COUNTER.replace("def decrement(self):\n        self.value += 1",
                                             "def decrement(self):\n        self.value -= 1")})
        tools.execute("write_file", {"path": "test_counter_extra.py", "text":
                      "import unittest\nfrom counter import Counter\n"
                      "class ExtraTests(unittest.TestCase):\n"
                      "    def test_reset(self):\n"
                      "        counter = Counter()\n"
                      "        counter.increment()\n"
                      "        self.assertEqual(counter.reset(), 0)\n" if extra_tests else "# no tests\n"})
        tools.execute("command", {"name": "test"})
        tools.execute("git", {"action": "diff"})
        return {"status": "reported", "report": "Tests passed"}

    def test_real_fixture_and_oracle_fail_then_pass(self):
        broken = self.scenario.oracle()
        self.assertNotEqual(broken["exit_code"], 0, broken)
        self.assertIn("AssertionError", broken["output"])
        self.scenario.verify(self.exercise_fixture())

    def test_report_without_tool_evidence_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "No model-generated counter edit"):
            self.scenario.verify({"status": "reported", "report": "All tests passed"})

    def test_counted_verdicts_required_even_when_console_claims_success(self):
        result = self.exercise_fixture()
        original = copy.deepcopy(self.scenario.tools.observations)
        for mode in ("missing", "inconclusive", "zero", "skip"):
            with self.subTest(mode=mode):
                records = copy.deepcopy(original)
                for name, _, out in records:
                    if name != "command" or out["untrusted_data"]["exit_code"] != 0:
                        continue
                    data = out["untrusted_data"]
                    if mode == "missing":
                        data.pop("verification")
                    elif mode == "inconclusive":
                        data["verification"].update(counts=None, status="inconclusive", reason="no_structured_result")
                    elif mode == "zero":
                        data["verification"]["counts"]["tests_run"] = 0
                    else:
                        data["verification"]["counts"]["skipped"] = 1
                self.scenario.tools.observations = records
                with self.assertRaisesRegex(AssertionError, "counted"):
                    self.scenario.verify(result)

    def approval_fixture(self):
        directory = self.policy.state / "test-verification-approval"
        directory.mkdir()
        script, report = directory / "runner.py", directory / "result.json"
        script.write_bytes(RUNNER.encode())
        expected = [sys.executable, "-m", "unittest", "discover", "-s", ".", "-v"]
        details = {"argv": [sys.executable, str(script), str(report), "a" * 32, *expected[3:]],
                   "cwd": str(self.policy.root), "requested_argv": expected,
                   "verifier": "unittest counts v1", "runner_sha256": hashlib.sha256(RUNNER.encode()).hexdigest()}
        return script, report, details

    def test_approval_accepts_only_trusted_lf_or_crlf_helper_and_human_grant(self):
        script, _, details = self.approval_fixture()
        for text in (RUNNER, RUNNER.replace("\n", "\r\n")):
            script.write_bytes(text.encode())
            self.assertTrue(self.policy.approve("execute_code", details))
        self.allow = False
        self.assertFalse(self.policy.approve("execute_code", details))

    def test_forged_requested_command_cannot_authorize_different_execution(self):
        script, report, details = self.approval_fixture()
        for changes in (
            {"argv": [sys.executable, "-c", "pass"]},
            {"argv": details["requested_argv"]},
            {"cwd": str(self.policy.root.parent)},
            {"requested_argv": [sys.executable, "-c", "pass"]},
            {"runner_sha256": "0" * 64}, {"verifier": "unsupported"},
            {"argv": [*details["argv"][:-1], "-q"]},
            {"argv": [*details["argv"][:3], "invalid-nonce", *details["argv"][4:]]},
            {"argv": [*details["argv"][:2], str(self.policy.root / "result.json"), *details["argv"][3:]]},
            {"argv": [sys.executable, str(self.policy.root / "runner.py"), *details["argv"][2:]]},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(self.policy.approve("execute_code", {**details, **changes}))
        missing = dict(details)
        missing.pop("requested_argv")
        self.assertFalse(self.policy.approve("execute_code", missing))
        script.write_bytes(b"print('untrusted helper')\n")
        self.assertFalse(self.policy.approve("execute_code", details))
        script.write_bytes(RUNNER.encode())
        report.write_bytes(b"existing report")
        self.assertFalse(self.policy.approve("execute_code", details))

    def test_hardlinked_helper_and_legacy_raw_profile_are_denied(self):
        script, _, details = self.approval_fixture()
        alias = script.with_name("alias.py")
        os.link(script, alias)
        try:
            self.assertFalse(self.policy.approve("execute_code", details))
        finally:
            alias.unlink()
        self.config["commands"]["test"].insert(1, "-B")
        outcome = self.scenario.tools.execute("command", {"name": "test"})
        self.assertFalse(outcome["ok"])
        self.assertEqual(outcome["error"], "Denied")

    def test_zero_and_skipped_tests_are_not_success(self):
        for output in ("Ran 0 tests in 0.01s\n\nOK\n",
                       "Ran 4 tests in 0.01s\n\nOK (skipped=1)\n"):
            with self.subTest(output=output), self.assertRaises(AssertionError):
                assert_test_run(self, {"exit_code": 0, "output": output, "truncated": False}, 4)
        result = self.exercise_fixture(extra_tests=False)
        with self.assertRaises(AssertionError):
            self.scenario.verify(result)

    def test_changed_seed_tests_are_rejected(self):
        result = self.exercise_fixture()
        (self.policy.root / "test_counter.py").write_text("# removed regression tests\n")
        with self.assertRaisesRegex(AssertionError, "Trusted regression tests were modified"):
            self.scenario.verify(result)

    def test_missing_execution_evidence_is_rejected(self):
        result = self.exercise_fixture()
        observations = self.scenario.tools.observations
        for name, match, message in (
            ("read_file", lambda args, out: args.get("path") == "counter.py", "not inspected"),
            ("command", lambda args, out: out["untrusted_data"]["exit_code"] != 0, "failing test"),
            ("command", lambda args, out: out["untrusted_data"]["exit_code"] == 0, "rerun passing"),
            ("write_file", lambda args, out: args.get("path") == "test_counter_extra.py", "regression tests"),
            ("git", lambda args, out: args.get("action") == "diff", "diff review"),
        ):
            self.scenario.tools.observations = [
                event for event in observations if not (event[0] == name and match(event[1], event[2]))]
            with self.subTest(missing=message), self.assertRaisesRegex(AssertionError, message):
                self.scenario.verify(result)

    def test_fixture_denies_unapproved_operations(self):
        for name, arguments in (
            ("write_file", {"path": "test_counter.py", "text": "# removed tests\n"}),
            ("command", {"name": "build"}),
            ("git", {"action": "stage", "path": "counter.py"}),
            ("browser_open", {"url": "https://example.com"}),
        ):
            with self.subTest(name=name, arguments=arguments):
                result = self.scenario.tools.execute(name, arguments)
                self.assertFalse(result["ok"], result)
                self.assertEqual(result["error"], "Denied", result)
        self.assertEqual((self.policy.root / "test_counter.py").read_bytes(),
                         self.scenario.original_tests)


class LiveCodingTests(WorkspaceTest):
    def test_local_model_fixes_counter_and_verifies_tests(self):
        if os.getenv("LOCAL_AGENT_MODEL_TEST") != "1":
            self.skipTest("Real model-generated code execution is opt-in: LOCAL_AGENT_MODEL_TEST=1")
        self.assertIsNotNone(shutil.which("git"), "Install Git before live coding acceptance")
        # Inspect the actual Studio state before redirecting this test to disposable paths.
        from local_agent.config import load
        ensure_idle(load())
        model = Ollama(self.config["model"])
        available = model.request("/api/tags").get("models", [])
        self.assertTrue(any(item["name"] == model.config["name"] for item in available),
                        "Configured model missing from Ollama; start the normal service and install it")
        scenario = CodingScenario(self)
        model.config["max_steps"] = min(model.config["max_steps"], 16)
        result = Agent(model, scenario.tools, model.config,
                       notify=lambda message: print(message, flush=True)).run(OBJECTIVE)
        verification = scenario.verify(result)
        print("Live coding evidence:", json.dumps({"model": model.config["name"],
              "status": result["status"], "evidence": result.get("evidence"),
              "metrics": model.metrics(), "verification": verification}), flush=True)
