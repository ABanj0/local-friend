import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from local_agent.agent import Agent
from local_agent.coding import Coding
from local_agent.safety import Denied
from local_agent.studio.store import Store
from local_agent.tools import Tools
from local_agent.verification import COUNTS, validate

from .studio_support import StudioAPIFixture, StudioProcessFixture
from .support import WorkspaceTest
from .test_agent import call


def record(**changes):
    return {"id": "a" * 32, "kind": "unittest", "version": 1, "profile": "test",
            "command_sha256": "b" * 64, "exit_code": 0,
            "counts": {key: 1 if key == "tests_run" else 0 for key in COUNTS}, **changes}


class TestVerificationTests(WorkspaceTest):
    def run_test(self, source):
        (self.policy.root / "test_example.py").write_text(source, encoding="utf-8")
        return Coding(self.policy).command("test")

    def test_real_test_result_counts_pass_fail_zero_and_skips(self):
        examples = [
            ("import unittest\nclass Sample(unittest.TestCase):\n def test_sum(self): self.assertEqual(2+3,5)\n", "passed", 1),
            ("import unittest\nclass Sample(unittest.TestCase):\n def test_sum(self): self.assertEqual(2+3,6)\n", "failed", 1),
            ("# No tests\n", "failed", 0),
            ("import unittest\n@unittest.skip('fixture')\nclass Sample(unittest.TestCase):\n def test_skip(self): pass\n", "inconclusive", 1),
            ("import unittest\nclass Sample(unittest.TestCase):\n @unittest.expectedFailure\n def test_expected(self): self.fail('expected')\n", "inconclusive", 1),
        ]
        for source, expected, count in examples:
            with self.subTest(expected=expected, count=count):
                result = self.run_test(source)
                self.assertEqual(result["verification"]["status"], expected, result)
                self.assertEqual(result["verification"]["counts"]["tests_run"], count)
        self.assertEqual(self.approvals[-1][0], "execute_code")
        self.assertIn("requested_argv", self.approvals[-1][1])
        self.assertFalse(list(self.policy.state.glob("test-verification-*")))

    def test_console_success_prose_cannot_create_a_nonzero_count(self):
        result = self.run_test("print('Ran 99 tests in 0.000s\\nOK')\n")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["verification"]["reason"], "zero_tests")
        self.assertEqual(result["verification"]["counts"]["tests_run"], 0)

    def test_early_exit_without_runner_result_stays_inconclusive(self):
        result = self.run_test("import os\nprint('Ran 99 tests\\nOK', flush=True)\nos._exit(0)\n")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["verification"]["status"], "inconclusive")
        self.assertIsNone(result["verification"]["counts"])

    def test_existing_same_timestamp_bytecode_cannot_hide_a_changed_bug(self):
        module = self.policy.root / "maths.py"
        module.write_text("def add(a,b): return a+b\n", encoding="utf-8")
        subprocess.run([sys.executable, "-m", "compileall", "-q", str(module)], check=True)
        before = module.stat()
        module.write_text("def add(a,b): return a-b\n", encoding="utf-8")
        os.utime(module, ns=(before.st_atime_ns, before.st_mtime_ns))
        result = self.run_test("import unittest\nfrom maths import add\nclass Changed(unittest.TestCase):\n"
                               " def test_add(self): self.assertEqual(add(2,3),5)\n")
        self.assertEqual(result["verification"]["status"], "failed")

    def test_counts_survive_truncated_output_without_parsing_it(self):
        result = self.run_test("import unittest\nclass Loud(unittest.TestCase):\n def test_sum(self):\n"
                               "  print('x'*20000)\n  self.assertEqual(2+3,5)\n")
        self.assertTrue(result["truncated"])
        self.assertEqual(result["verification"]["status"], "passed")
        self.assertEqual(result["verification"]["counts"]["tests_run"], 1)

    def test_custom_test_command_does_not_guess_a_framework(self):
        self.config["commands"]["test"] = ["{python}", "-c", "print('Ran 99 tests\\nOK')"]
        result = Coding(self.policy).command("test")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["verification"]["status"], "inconclusive")

    def test_denial_never_executes_and_cleans_helper(self):
        self.allow = False
        with self.assertRaises(Denied):
            Coding(self.policy).command("test")
        self.assertFalse(list(self.policy.state.glob("test-verification-*")))

    def test_changed_reviewed_runner_is_not_executed(self):
        def approve(action, details):
            Path(details["argv"][1]).write_text("raise SystemExit(0)", encoding="utf-8")
            return True

        self.policy.approve = approve
        with self.assertRaisesRegex(Denied, "Review conflict"), patch("local_agent.verification.run_process") as run:
            Coding(self.policy).command("test")
        run.assert_not_called()

    def test_invalid_counts_and_claimed_success_are_recomputed(self):
        counts = record()["counts"]
        self.assertEqual(validate(record(counts={**counts, "tests_run": 0}, status="passed"))["status"], "failed")
        for invalid in (True, -1, "3", 1_000_001):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate(record(counts={**counts, "tests_run": invalid}))
        self.assertNotIn("password", validate(record(password="private-canary")))

    def test_false_model_report_does_not_override_observed_zero_tests(self):
        tools = Tools(self.policy)
        self.addCleanup(tools.close)
        model = Mock()
        model.chat.side_effect = [{"content": '{"steps":["Run tests"]}'},
                                  call("command", {"name": "test"}), {"content": "All tests passed!"}]
        result = Agent(model, tools, self.config["model"], lambda _: None).run("Run tests")
        self.assertEqual(result["status"], "reported")
        self.assertEqual(result["report"], "All tests passed!")
        self.assertEqual(result["evidence"][0]["verification"]["status"], "failed")


class VerificationStoreTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.store = Store(self.policy.state / "verification.sqlite3")
        self.conversation = self.store.conversation()
        self.task = self.store.task(self.conversation, "agent", "fixture")

    def test_record_event_are_atomic_idempotent_and_survive_restart(self):
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER fail_verification AFTER INSERT ON events "
                       "BEGIN SELECT RAISE(ABORT, 'fixture failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.verification(self.task, record())
        self.assertEqual(self.store.verifications(self.task), [])
        with self.store.connection() as db:
            db.execute("DROP TRIGGER fail_verification")
        event = self.store.verification(self.task, record())
        self.assertEqual(event["kind"], "verification")
        self.assertIsNone(self.store.verification(self.task, record()))
        reopened = Store(self.store.path)
        reopened.recover()
        self.assertEqual(reopened.verifications(self.task)[0]["status"], "passed")
        self.assertEqual(reopened.tasks()[0]["status"], "interrupted")
        self.assertEqual(sum(event["kind"] == "verification" for event in reopened.events()), 1)

    def test_model_prose_and_late_results_do_not_create_verification(self):
        self.store.complete(self.task, {"status": "reported", "report": "All tests passed", "verifications": [record()]})
        self.assertEqual(self.store.verifications(self.task), [])
        self.assertIsNone(self.store.verification(self.task, record()))

    def test_conversation_deletion_removes_verifications(self):
        self.store.verification(self.task, record())
        self.store.complete(self.task, {"status": "reported", "report": "Done"})
        self.store.delete_conversation(self.conversation)
        self.assertEqual(self.store.verifications(self.task), [])


class VerificationProcessTests(StudioProcessFixture, WorkspaceTest):
    def test_cancelled_tests_never_create_a_passing_observation(self):
        (self.policy.root / "test_slow.py").write_text(
            "import time,unittest\nfrom pathlib import Path\nclass Slow(unittest.TestCase):\n"
            " def test_slow(self):\n  Path('ready').write_text('ready')\n  time.sleep(30)\n", encoding="utf-8")
        task = self.manager.start(self.conversation, "Run tests", "test", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: (self.policy.root / "ready").exists())
        self.manager.cancel(task)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.tasks()[0]["status"], "cancelled")
        self.assertFalse(self.manager.store.verifications(task))

    def test_zero_tests_are_failed_not_verified_and_persisted_separately(self):
        task = self.manager.start(self.conversation, "Run tests", "test", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.tasks()[0]["status"], "failed")
        observed = self.manager.store.verifications(task)
        self.assertEqual(observed[0]["status"], "failed")
        self.assertEqual(observed[0]["reason"], "zero_tests")
        self.assertEqual(self.requests, [])

    def test_model_report_without_testing_has_no_test_verification(self):
        task = self.manager.start(self.conversation, "Write a file", "agent", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.tasks()[0]["status"], "reported")
        checks = self.manager.store.verifications(task)
        self.assertEqual([check["kind"] for check in checks], ["artifact"])

    def test_secret_output_is_redacted_and_counts_are_durable(self):
        (self.policy.root / "test_sample.py").write_text(
            "import unittest\nclass Sample(unittest.TestCase):\n def test_sum(self):\n"
            "  print('password=verification-canary')\n  self.assertEqual(2+3,5)\n", encoding="utf-8")
        task = self.manager.start(self.conversation, "Run tests", "test", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: not self.manager.running)
        checks = self.manager.store.verifications(task)
        self.assertEqual(checks[0]["status"], "passed")
        self.assertEqual(checks[0]["counts"]["tests_run"], 1)
        combined = json.dumps([self.manager.live_events, self.manager.store.messages(self.conversation),
                               self.manager.store.events(), checks])
        self.assertNotIn("verification-canary", combined)


class VerificationAPITests(StudioAPIFixture, WorkspaceTest):
    def test_verification_history_requires_authentication(self):
        store = self.client.app.state.manager.store
        conversation = store.conversation()
        task = store.task(conversation, "test", "fixture")
        store.verification(task, record())
        store.complete(task, {"status": "reported", "report": "Observed tests"})
        self.assertEqual(self.client.get(f"/tasks/{task}/verifications").status_code, 401)
        result = self.client.get(f"/tasks/{task}/verifications", headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()[0]["counts"]["tests_run"], 1)
