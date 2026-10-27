import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from local_agent.studio.process_output import ProcessOutput

from .studio_support import StudioAPIFixture
from .support import WorkspaceTest


class ProcessOutputTests(unittest.TestCase):
    def setUp(self):
        self.output = ProcessOutput()
        self.addCleanup(self.output.close)

    def start(self, source):
        self.output.start([sys.executable, "-u", "-c", source], dict(os.environ))

    def test_real_pipe_redacts_split_secrets_and_bounds_no_newline_output(self):
        self.start("import sys,time; print('x'*100000,end=''); "
                   "sys.stdout.write(' password='); sys.stdout.flush(); time.sleep(.05); "
                   "sys.stderr.write('canary-private-value\\nhealthy\\n'); sys.stderr.flush()")
        self.output.proc.wait(5)
        self.output.reader.join(5)
        status = self.output.snapshot()
        self.assertEqual(status["exit_code"], 0)
        self.assertIn("healthy", status["output"])
        self.assertNotIn("canary-private-value", status["output"])
        self.assertLessEqual(len(status["output"]), self.output.LIMIT)

    def test_repeated_start_and_stop_leave_unrelated_process_alive(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        self.addCleanup(unrelated.wait, 5)
        self.addCleanup(unrelated.terminate)
        self.start("import time; print('ready'); time.sleep(30)")
        first = self.output.proc
        self.assertFalse(self.output.start(["does-not-exist"], dict(os.environ)))
        self.assertIs(self.output.proc, first)
        self.output.close()
        self.assertIsNotNone(first.poll())
        self.assertFalse(self.output.reader.is_alive())
        self.assertIsNone(unrelated.poll())
        self.start("print('next')")
        self.output.proc.wait(5)
        self.output.close()
        self.assertIn("next", self.output.snapshot()["output"])

    @unittest.skipUnless(os.name == "nt", "Windows owned Job Object failure")
    def test_job_failure_reaps_new_child_and_closes_pipe(self):
        with (patch("local_agent.windows_job.WindowsJob", side_effect=OSError("fixture job failure")),
              self.assertRaises(OSError)):
            self.start("import time; time.sleep(30)")
        self.assertIsNotNone(self.output.proc.poll())
        self.assertTrue(self.output.proc.stdout.closed)

    def test_partial_secret_is_never_emitted_on_stop(self):
        self.start("import sys,time; sys.stdout.write('password=partial-canary'); "
                   "sys.stdout.flush(); time.sleep(30)")
        deadline = time.monotonic() + 5
        while "[REDACTED]" not in self.output.snapshot()["output"] and time.monotonic() < deadline:
            time.sleep(.02)
        self.output.close()
        self.assertIn("[REDACTED]", self.output.snapshot()["output"])
        self.assertNotIn("partial-canary", self.output.snapshot()["output"])


class ModelDiagnosticsAPITests(StudioAPIFixture, WorkspaceTest):
    def test_diagnostics_are_authenticated_and_model_connection_errors_redacted(self):
        with patch("local_agent.studio.api.Ollama.request", side_effect=OSError("offline password=api-canary")):
            self.assertEqual(self.client.get("/models").status_code, 401)
            result = self.client.get("/models", headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()["running"])
        self.assertFalse(result.json()["diagnostics"]["owned"])
        self.assertNotIn("api-canary", result.text)

    def test_existing_service_is_never_started_or_owned(self):
        with (patch("local_agent.studio.api.Ollama.request", return_value={"models": []}),
              patch("local_agent.studio.process_output.subprocess.Popen") as spawn):
            result = self.client.post("/models/start", headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()["started"])
        spawn.assert_not_called()
