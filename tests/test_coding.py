import shutil
import sys
import threading
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.process import run_process
from local_agent.safety import Denied, Stopped

from .support import WorkspaceTest


class CodingTests(WorkspaceTest):
    def test_frozen_python_uses_configured_external_runtime(self):
        with patch.object(sys, "frozen", True, create=True):
            self.policy.config["runtime"] = {"python": sys.executable}
            self.assertEqual(Coding(self.policy).python(), sys.executable)

    def test_frozen_python_missing_runtime_is_actionable(self):
        with (patch.object(sys, "frozen", True, create=True),
              patch("local_agent.coding.shutil.which", return_value=None),
              self.assertRaisesRegex(ValueError, "configure.*runtime")):
            Coding(self.policy).python()

    def test_bug_fix_cycle_in_real_git_repository(self):
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        coding = Coding(self.policy)
        self.assertEqual(coding.git("init")["exit_code"], 0)
        coding.write("maths.py", "def add(a, b):\n    return a - b\n")
        coding.write("test_maths.py", "import unittest\nfrom maths import add\n"
                     "class AdditionTests(unittest.TestCase):\n"
                     "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n")
        broken = coding.command("test")
        self.assertNotEqual(broken["exit_code"], 0, broken)
        self.assertIn("AssertionError", broken["output"])
        coding.write("maths.py", "def add(a, b):\n    return sum((a, b))\n")
        fixed = coding.command("test")
        self.assertEqual(fixed["exit_code"], 0, fixed)
        self.assertIn("OK", fixed["output"])
        self.assertEqual(coding.command("build")["exit_code"], 0)
        self.assertIn("maths.py", coding.git("status")["output"])
        self.assertEqual(coding.git("diff")["exit_code"], 0)
        self.assertTrue(any(action == "overwrite_file" for action, _ in self.approvals))

    def test_background_process_cleanup(self):
        self.config["commands"]["wait"] = ["{python}", "-c", "import time; time.sleep(20)"]
        coding = Coding(self.policy)
        self.addCleanup(coding.close)
        result = coding.start("wait")
        proc = coding.processes["wait"].proc
        self.assertEqual(result["pid"], proc.pid)
        self.assertIsNone(proc.poll())
        coding.close()
        self.assertIsNotNone(proc.poll())

    def test_git_stage_review_commit_in_disposable_repository(self):
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        coding = Coding(self.policy)
        self.assertEqual(coding.git("init")["exit_code"], 0)
        for key, value in (("user.name", "Local Agent Test"), ("user.email", "test@example.invalid")):
            result = run_process([shutil.which("git"), "config", "--local", key, value],
                                 self.policy.root, self.policy)
            self.assertEqual(result["exit_code"], 0, result)
        coding.write("sample.txt", "review this test content\n")
        self.assertEqual(coding.git("stage", path="sample.txt")["exit_code"], 0)
        result = coding.git("commit", message="Add test fixture")
        self.assertEqual(result["exit_code"], 0, result)
        reviews = [details for action, details in self.approvals if action == "git_commit"]
        self.assertIn("review this test content", reviews[0]["staged_diff"]["output"])
        self.assertEqual(coding.git("status")["output"].strip(), "")

    def test_command_profile_cannot_be_injected(self):
        with self.assertRaises(Denied):
            Coding(self.policy).command("test; whoami")

    def test_process_timeout(self):
        with self.assertRaises(TimeoutError):
            run_process([sys.executable, "-c", "import time; time.sleep(10)"],
                        self.policy.root, self.policy, timeout=0.15)

    def test_process_stop(self):
        timer = threading.Timer(0.15, self.policy.stop_event.set)
        timer.start()
        self.addCleanup(timer.cancel)
        with self.assertRaises(Stopped):
            run_process([sys.executable, "-c", "import time; time.sleep(10)"],
                        self.policy.root, self.policy)

    def test_files_readback(self):
        coding = Coding(self.policy)
        coding.write("src/example.py", "answer = 42\n")
        self.assertEqual(coding.read("src/example.py")["text"], "answer = 42\n")
        self.assertEqual(len(coding.files()["files"]), 1)
