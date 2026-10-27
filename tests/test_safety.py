import json
from pathlib import Path

from local_agent.safety import Denied, Policy, Stopped, redact
from local_agent.tools import Tools

from .support import WorkspaceTest


class SafetyTests(WorkspaceTest):
    def test_escape_and_sensitive_paths(self):
        for path in ("../secret", "C:\\Windows\\win.ini", "//host/share", "file:stream", ".env",
                     "repo/.git/config", "x/key.pem", "NUL.txt", "file.", "file "):
            with self.subTest(path=path), self.assertRaises(Denied):
                self.policy.path(path)

    def test_regular_relative_path(self):
        self.assertEqual(self.policy.path("src/main.py"), self.policy.root / "src" / "main.py")

    def test_symlink_escape(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        try:
            (self.policy.root / "link").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Windows symlink creation unavailable")
        with self.assertRaises(Denied):
            self.policy.path("link/file")

    def test_hardlink_denied(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("private")
        (self.policy.root / "alias.txt").hardlink_to(outside)
        with self.assertRaises(Denied):
            self.policy.path("alias.txt", write=True)

    def test_default_approval_denies(self):
        with self.assertRaises(Denied):
            Policy(self.config).confirm("purchase", {})

    def test_origin_boundaries(self):
        self.assertEqual(self.policy.origin("https://example.com/path"), "https://example.com")
        for url in ("file:///secret", "https://example.com.evil.test", "https://user:pass@example.com",
                    "http://127.0.0.1:9999", "https://example.com:123"):
            with self.subTest(url=url), self.assertRaises(Denied):
                self.policy.origin(url)

    def test_emergency_stop(self):
        (self.policy.state / "STOP").touch()
        with self.assertRaises(Stopped):
            self.policy.path("file")

    def test_audit_contains_no_arguments(self):
        self.policy.audit("read_file", {"password": "secret-canary"}, "ok")
        raw = (self.policy.state / "audit.jsonl").read_text()
        self.assertNotIn("secret-canary", raw)
        self.assertNotIn("password", raw)
        self.assertEqual(json.loads(raw)["status"], "ok")

    def test_redaction(self):
        text = redact("password=canary api_key=abc Bearer abcdef.123")
        self.assertNotIn("canary", text)
        self.assertNotIn("abcdef", text)

    def test_unknown_tools_and_types(self):
        tools = Tools(self.policy)
        self.assertFalse(tools.execute("shell", {"cmd": "del *"})["ok"])
        self.assertFalse(tools.execute("write_file", {"path": 4, "text": "x"})["ok"])
        self.assertFalse(tools.execute("files", {"unexpected": "x"})["ok"])

    def test_denied_write_leaves_existing_file(self):
        tools = Tools(self.policy)
        tools.execute("write_file", {"path": "safe.txt", "text": "old"})
        self.allow = False
        result = tools.execute("write_file", {"path": "safe.txt", "text": "new"})
        self.assertEqual(result["error"], "Denied")
        self.assertEqual((self.policy.root / "safe.txt").read_text(), "old")
