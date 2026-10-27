"""Opt-in acceptance against the real PyInstaller sidecar and approved external Python."""
import json
import os
import sys
import time
import unittest
from urllib.request import Request

from .fixture_site import FixtureSite
from .studio_socket_support import StudioSocketFixture
from .support import WorkspaceTest


@unittest.skipUnless(os.getenv("FROZEN_BACKEND_TEST_EXE"), "Build/select a frozen backend explicitly")
class FrozenCodingTests(StudioSocketFixture, WorkspaceTest):
    def start_backend(self):
        text = self.socket_config.read_text(encoding="utf-8")
        if "[runtime]" not in text:
            text += "\n[runtime]\npython = " + json.dumps(sys.executable) + "\n"
            self.socket_config.write_text(text, encoding="utf-8")
        super().start_backend()

    def post(self, path, body):
        request = Request(f"http://127.0.0.1:{self.port}{path}", data=json.dumps(body).encode(),
                          headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def test_frozen_worker_runs_approved_external_python_and_preserves_history(self):
        (self.policy.root / "test_external.py").write_text(
            "import sys, unittest\nclass External(unittest.TestCase):\n"
            " def test_external(self):\n  self.assertFalse(getattr(sys, 'frozen', False))\n"
            "  self.assertEqual(2+3,5)\n", encoding="utf-8")
        conversation = self.post("/conversations", {"title": "Frozen external Python acceptance"})["id"]
        task = self.post("/tasks", {"conversation": conversation, "objective": "Run tests",
                                   "mode": "test", "model": "not-used"})["id"]
        approval = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            data = self.http("/tasks")
            approval = next((a for a in data["approvals"] if a["task"] == task), None)
            if approval:
                break
            time.sleep(.05)
        self.assertIsNotNone(approval, data)
        self.assertEqual(approval["action"], "execute_code")
        self.assertEqual(approval["details"]["argv"][0], sys.executable)
        self.post(f"/tasks/{task}/approvals/{approval['id']}", {"approved": True})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            row = next(row for row in self.http("/tasks")["tasks"] if row["id"] == task)
            if row["status"] not in {"running", "waiting"}:
                break
            time.sleep(.05)
        self.assertEqual(row["status"], "reported", row)
        report = self.http(f"/conversations/{conversation}/messages")[-1]["content"]
        self.assertIn("Ran 1 test", report)
        self.assertIn("OK", report)
        checks = self.http(f"/tasks/{task}/verifications")
        self.assertEqual(checks[0]["status"], "passed")
        self.assertEqual(checks[0]["counts"]["tests_run"], 1)
        self.stop_backend()
        self.start_backend()
        self.assertEqual(self.http(f"/conversations/{conversation}/messages")[-1]["content"], report)
        self.assertEqual(self.http(f"/tasks/{task}/verifications")[0]["id"], checks[0]["id"])


@unittest.skipUnless(os.getenv("FROZEN_BACKEND_TEST_EXE") and os.getenv("FROZEN_LIVE_MODEL") == "1",
                     "Actual model/frozen browser workflow is opt-in")
class FrozenBrowserTests(StudioSocketFixture, WorkspaceTest):
    def start_backend(self):
        if not hasattr(self, "site"):
            self.site = self.enterContext(FixtureSite())
        text = self.socket_config.read_text(encoding="utf-8")
        text = text.replace('headless = true', 'headless = true\nchannel = "msedge"')
        text = text.replace('allowed_origins = [', 'allowed_origins = [' + json.dumps(self.site.url) + ', ')
        self.socket_config.write_text(text, encoding="utf-8")
        super().start_backend()

    def test_real_model_browser_and_screenshot_in_frozen_worker(self):
        def post(path, body):
            request = Request(f"http://127.0.0.1:{self.port}{path}", data=json.dumps(body).encode(),
                              headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"})
            with self.opener.open(request, timeout=10) as response:
                return json.load(response)

        conversation = post("/conversations", {"title": "Frozen browser acceptance"})["id"]
        task = post("/tasks", {"conversation": conversation, "mode": "agent",
                               "model": self.config["model"]["name"], "objective":
                               f"Use browser_open to open {self.site.url}, then use browser_screenshot. "
                               "Read the heading and report it. Do not submit forms or write files."})["id"]
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            row = next(row for row in self.http("/tasks")["tasks"] if row["id"] == task)
            if row["status"] not in {"running", "waiting"}:
                break
            time.sleep(.1)
        self.assertEqual(row["status"], "reported", row)
        result = json.loads(row["result"])
        successful = {item["tool"] for item in result["evidence"] if item["ok"]}
        self.assertTrue({"browser_open", "browser_screenshot"} <= successful, result)
        self.assertIn("Local Agent Test", result["report"])
        self.assertFalse(list((self.policy.state / "captures").glob("*/*.png")))
