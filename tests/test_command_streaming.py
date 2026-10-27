"""Real approved commands and durable streaming; no model inference required."""
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.command_output import LIMIT, CommandOutput, accept_event
from local_agent.process import run_process
from local_agent.safety import Denied, Stopped
from local_agent.studio.store import Store

from .studio_support import StudioProcessFixture
from .support import WorkspaceTest


class CommandStreamingTests(WorkspaceTest):
    def run_source(self, source, **kwargs):
        return run_process([sys.executable, "-c", source], self.policy.root, self.policy, **kwargs)

    def test_output_arrives_before_exit_and_final_text_matches_deltas(self):
        frames = []
        marker = self.policy.root / "continue"

        def observe(frame):
            frames.append(frame)
            if "LIVE-READY" in frame["text"]:
                self.assertFalse(marker.exists())
                marker.touch()

        result = self.run_source("from pathlib import Path\nimport time\nprint('LIVE-READY '+'.'*40)\n"
                                 "while not Path('continue').exists(): time.sleep(.02)\nprint('finished')",
                                 timeout=4, on_output=observe)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual("".join(frame["text"] for frame in frames), result["output"])
        self.assertEqual(frames[-1]["reason"], "completed")
        self.assertTrue(frames[-1]["finished"])
        self.assertEqual([frame["part"] for frame in frames], list(range(1, len(frames) + 1)))

    def test_large_no_newline_output_is_drained_without_unbounded_file_capture(self):
        frames = []
        result = self.run_source("import os; os.write(1,b'x'*1000000)", on_output=frames.append)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["output"], "x" * LIMIT)
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(frames), 64)
        self.assertEqual(sum(len(frame["text"].encode()) for frame in frames), LIMIT)
        self.assertFalse(list(self.policy.root.iterdir()))

    def test_utf8_and_secret_split_across_real_stdout_stderr_never_leaks(self):
        frames = []
        result = self.run_source("import os,time\nraw='snowman \\u2603\\npassword='.encode()\n"
                                 "os.write(1,raw[:9]); time.sleep(.05); os.write(1,raw[9:]); time.sleep(.05)\n"
                                 "os.write(2,b'COMMAND-SECRET-CANARY\\nhealthy\\n')", on_output=frames.append)
        combined = json.dumps(frames, ensure_ascii=False) + result["output"]
        self.assertNotIn("COMMAND-SECRET-CANARY", combined)
        self.assertIn("snowman \u2603", result["output"])
        self.assertIn("healthy", result["output"])
        self.assertIn("[REDACTED]", result["output"])

    def test_capture_boundary_does_not_publish_partial_credential_or_invalid_utf8(self):
        output = CommandOutput()
        output.drain(io.BytesIO(b"x" * (LIMIT - 10) + b" password=PARTIAL-CANARY"))
        text, truncated = output.snapshot()
        self.assertNotIn("PARTIAL-CANARY", text)
        self.assertTrue(truncated)
        self.assertLessEqual(len(text.encode()), LIMIT)
        output = CommandOutput()
        output.drain(io.BytesIO(b"\xff" * 20_000))
        text, truncated = output.snapshot()
        self.assertLessEqual(len(text.encode()), LIMIT)
        self.assertTrue(truncated)

    def test_event_budget_keeps_final_unsent_tail(self):
        frames = []
        with patch("local_agent.process.MAX_PARTS", 4):
            result = self.run_source("import time\nfor i in range(16):\n print(str(i)+'.'*40); time.sleep(.08)",
                                     on_output=frames.append)
        self.assertLessEqual(len(frames), 4)
        self.assertEqual("".join(frame["text"] for frame in frames), result["output"])
        self.assertTrue(frames[-1]["finished"])

    def test_stop_preserves_only_safe_partial_output_and_reaps_process(self):
        frames = []

        def observe(frame):
            frames.append(frame)
            if "STOP-READY" in frame["text"]:
                self.policy.stop_event.set()

        start = time.monotonic()
        with self.assertRaises(Stopped):
            self.run_source("import time,sys\nprint('STOP-READY '+'.'*40)\n"
                            "sys.stdout.write('password=CANCEL-CANARY');sys.stdout.flush();time.sleep(30)",
                            on_output=observe)
        self.assertLess(time.monotonic() - start, 5)
        self.assertNotIn("CANCEL-CANARY", json.dumps(frames))
        self.assertEqual(frames[-1]["reason"], "cancelled")
        self.assertTrue(frames[-1]["finished"])

    def test_timeout_reports_safe_final_frame_and_does_not_kill_unrelated_process(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        self.addCleanup(unrelated.wait, 5)
        self.addCleanup(unrelated.terminate)
        frames = []
        with self.assertRaises(TimeoutError):
            self.run_source("import time;print('timeout-ready '+'.'*30);time.sleep(30)", timeout=.3,
                            on_output=frames.append)
        self.assertIsNone(unrelated.poll())
        self.assertEqual(frames[-1]["reason"], "timeout")
        self.assertTrue(frames[-1]["finished"])

    def test_child_that_inherits_stdout_is_cleaned_when_parent_exits(self):
        if os.name != "nt":
            self.skipTest("Windows owned Job Object subtree acceptance")
        import psutil

        source = "import os,time;from pathlib import Path;Path('child.pid').write_text(str(os.getpid()));time.sleep(30)"
        code = ("import subprocess,sys,time\nfrom pathlib import Path\ntime.sleep(.15)\n"
                f"subprocess.Popen([sys.executable,'-c',{source!r}])\n"
                "while not Path('child.pid').exists():time.sleep(.01)\nprint('parent finished')")
        result = self.run_source(code, timeout=5)
        pid = int((self.policy.root / "child.pid").read_text())
        self.assertEqual(result["exit_code"], 0)
        # Windows can retain a terminated process object briefly after pipe EOF.
        # Wait for actual termination; a live orphan sleeping 30s fails this bound.
        try:
            child = psutil.Process(pid)
            child.wait(timeout=2)
        except psutil.NoSuchProcess:
            pass

    def test_callback_failure_reaps_owned_process_and_does_not_retry_callback(self):
        def broken(frame):
            raise RuntimeError("fixture delivery failure")

        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "delivery failure"):
            self.run_source("import time;time.sleep(30)", on_output=broken)
        self.assertLess(time.monotonic() - started, 5)

    def test_denied_command_emits_no_frames_and_test_verifier_stays_independent(self):
        coding = Coding(self.policy)
        frames = []
        coding.output = frames.append
        self.allow = False
        with self.assertRaises(Denied):
            coding.command("test")
        self.assertFalse(frames)
        self.allow = True
        (self.policy.root / "test_sample.py").write_text("import unittest\nclass Sample(unittest.TestCase):\n"
            " def test_ok(self): print('live unittest output');self.assertTrue(True)\n", encoding="utf-8")
        result = coding.command("test")
        self.assertEqual(result["verification"]["counts"]["tests_run"], 1)
        self.assertEqual(result["verification"]["status"], "passed")
        self.assertTrue(all(frame["profile"] == "test" for frame in frames))

    def test_event_validation_is_transactional_and_rejects_malformed_or_excess_data(self):
        frame = {"command_id": "a" * 32, "part": 1, "text": "ready", "profile": "test", "truncated": False,
                 "finished": False, "exit_code": None, "reason": "running"}
        states = {}
        accept_event(frame, states)
        before = copy.deepcopy(states)
        for changes in ({"part": 1}, {"part": True}, {"part": 65}, {"text": "x" * LIMIT},
                        {"finished": True}, {"exit_code": 0}, {"profile": "other"}, {"reason": []}):
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError):
                accept_event({**frame, "part": 2, **changes}, states)
            self.assertEqual(states, before)
        accept_event(dict(frame, part=2, text="", finished=True, reason="completed", exit_code=0), states)
        with self.assertRaises(ValueError):
            accept_event(dict(frame, part=3), states)

    def test_internal_git_checks_use_original_config_and_raw_mode_never_streams(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("Git required for configuration policy regression")
        coding = Coding(self.policy)
        self.assertEqual(coding.git("init")["exit_code"], 0)
        versions = []
        for value in ("password=CONFIG-FIRST-CANARY", "password=CONFIG-SECOND-CANARY"):
            self.assertEqual(run_process([git, "config", "--local", "custom.note", value],
                                         self.policy.root, self.policy)["exit_code"], 0)
            versions.append(coding._git_config_version([git], self.policy.root))
        self.assertNotEqual(*versions)
        self.assertEqual(run_process([git, "config", "--local", "filter.local.process", "must-never-execute"],
                                     self.policy.root, self.policy)["exit_code"], 0)
        with self.assertRaisesRegex(Denied, "helper/include"):
            coding.git("status")
        frames = []
        with self.assertRaises(ValueError):
            self.run_source("print('must not run')", raw_output=True, on_output=frames.append)
        self.assertFalse(frames)

    def test_job_or_reader_start_failure_reaps_child_and_closes_pipe(self):
        real_spawn = subprocess.Popen
        spawned = []

        def spawn(*args, **kwargs):
            process = real_spawn(*args, **kwargs)
            if kwargs.get("stdout") == subprocess.PIPE:
                spawned.append(process)
            return process

        targets = ["local_agent.process.threading.Thread.start"]
        if os.name == "nt":
            targets.append("local_agent.windows_job.WindowsJob")
        for target in targets:
            with (self.subTest(target=target), patch("local_agent.process.subprocess.Popen", side_effect=spawn),
                  patch(target, side_effect=OSError("fixture startup failure")), self.assertRaises(OSError)):
                self.run_source("import time;time.sleep(30)")
            child = spawned[-1]
            self.assertIsNotNone(child.poll())
            self.assertTrue(child.stdout.closed)


class CommandStreamingProcessTests(StudioProcessFixture, WorkspaceTest):
    def start_test(self, source):
        (self.policy.root / "test_sample.py").write_text(source, encoding="utf-8")
        task = self.manager.start(self.conversation, "Run tests", "test", "fixture", profile="coding")
        self.wait_until(lambda: self.manager.pending())
        self.assertFalse([row for row in self.manager.store.events() if row["kind"] == "command_output"])
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        return task

    def test_output_is_durable_before_completion_and_survives_store_restart(self):
        task = self.start_test("import unittest,time\nfrom pathlib import Path\nclass Sample(unittest.TestCase):\n"
            " def test_live(self):\n  print('WORKER-LIVE '+'.'*40)\n"
            "  while not Path('continue').exists(): time.sleep(.02)\n  self.assertTrue(True)\n")
        self.wait_until(lambda: any("WORKER-LIVE" in row["payload"].get("text", "") for row in self.manager.store.events()
                                   if row["kind"] == "command_output"))
        self.assertTrue(self.manager.running)
        (self.policy.root / "continue").touch()
        self.wait_until(lambda: not self.manager.running)
        rows = [row for row in self.manager.store.events() if row["kind"] == "command_output"]
        self.assertTrue(rows[-1]["payload"]["finished"])
        self.assertEqual(rows[-1]["payload"]["exit_code"], 0)
        reopened = Store(self.policy.state / "studio.sqlite3")
        self.assertEqual([row for row in reopened.events() if row["kind"] == "command_output"], rows)
        self.assertEqual(reopened.verifications(task)[0]["counts"]["tests_run"], 1)

    def test_cancel_keeps_safe_partial_events_without_inventing_a_test_result(self):
        task = self.start_test("import unittest,time,sys\nclass Sample(unittest.TestCase):\n def test_wait(self):\n"
            "  print('CANCEL-WORKER '+'.'*40)\n  sys.stdout.write('password=WORKER-SECRET-CANARY');sys.stdout.flush()\n"
            "  time.sleep(30)\n")
        self.wait_until(lambda: any("CANCEL-WORKER" in row["payload"].get("text", "") for row in self.manager.store.events()
                                   if row["kind"] == "command_output"))
        self.manager.cancel(task)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(self.manager.tasks()[0]["status"], "cancelled")
        self.assertFalse(self.manager.store.verifications(task))
        self.assertNotIn("WORKER-SECRET-CANARY", json.dumps(self.manager.store.events()))
