"""Bounded search contracts and actual scoped worker execution; model replies are fixtures."""
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.safety import Denied, Policy, Stopped
from local_agent.tools import Tools

from .studio_support import StudioAPIFixture, StudioProcessFixture
from .support import WorkspaceTest


class RepositorySearchTests(WorkspaceTest):
    def search(self, query="needle", **kwargs):
        return Coding(self.policy).search(query, **kwargs)

    def test_literal_unicode_line_column_hash_and_single_file_no_mutation(self):
        target = self.policy.root / "source.py"
        text = "heading\r\n  needle [a+b] \u2603\r\nNeedle\n"
        target.write_bytes(text.encode())
        stamp = target.stat().st_mtime_ns
        result = self.search("needle")
        self.assertTrue(result["complete"])
        self.assertEqual([(m["path"], m["line"], m["column"]) for m in result["matches"]], [("source.py", 2, 3)])
        self.assertEqual(result["matches"][0]["sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(self.search("[a+b]")["matches"][0]["line"], 2)
        self.assertEqual(target.stat().st_mtime_ns, stamp)
        self.assertEqual(target.read_bytes(), text.encode())
        self.assertFalse(self.approvals)

    def test_project_scope_has_no_cross_project_results(self):
        for name in ("first", "second"):
            (self.policy.root / name).mkdir()
            (self.policy.root / name / "code.py").write_text("needle", encoding="utf-8")
        result = self.search(path="first")
        self.assertEqual([m["path"] for m in result["matches"]], [str(Path("first/code.py"))])
        for path in ("..", "C:\\Windows", ".git"):
            with self.subTest(path=path), self.assertRaises(Denied):
                self.search(path=path)

    def test_credentials_controls_dependencies_and_binary_are_excluded(self):
        for folder in (".git", ".aws", ".ssh", ".codex", ".agents", "node_modules", ".venv"):
            directory = self.policy.root / folder
            directory.mkdir()
            (directory / "private.txt").write_text("needle secret", encoding="utf-8")
        for name in (".env", ".env.local", ".npmrc", "private.key", "private.pem"):
            (self.policy.root / name).write_text("needle secret", encoding="utf-8")
        (self.policy.root / "binary.bin").write_bytes(b"needle\x00binary")
        (self.policy.root / "encoding.bin").write_bytes(b"needle\xff")
        (self.policy.root / "public.txt").write_text("needle public", encoding="utf-8")
        result = self.search()
        self.assertEqual([m["path"] for m in result["matches"]], ["public.txt"])
        self.assertEqual(result["skipped"]["nontext"], 2)
        self.assertTrue(result["skipped"]["excluded"])
        self.assertNotIn("needle secret", json.dumps(result))

    def test_internal_state_is_excluded_even_at_nonstandard_location(self):
        self.config["paths"]["state"] = str(self.policy.root / "internal-state")
        self.policy = Policy(self.config)
        (self.policy.state / "private.txt").write_text("needle secret", encoding="utf-8")
        result = self.search()
        self.assertFalse(result["matches"])
        self.assertEqual(result["skipped"]["excluded"], 1)
        with self.assertRaises(Denied):
            self.search(path="internal-state")

    def test_hardlinked_alias_is_never_opened(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("needle outside", encoding="utf-8")
        os.link(outside, self.policy.root / "alias.txt")
        with patch.object(Path, "open", side_effect=AssertionError("No content read allowed")):
            result = self.search()
        self.assertFalse(result["matches"])
        self.assertEqual(result["skipped"]["denied"], 1)

    def test_changed_during_read_is_omitted_and_reported(self):
        target = self.policy.root / "changing.txt"
        target.write_bytes(b"needle before")
        original_open = Path.open

        class ChangingReader:
            def __init__(self, source):
                self.source = source

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.source.close()

            def fileno(self):
                return self.source.fileno()

            def read(self, size):
                content = self.source.read(size)
                with original_open(target, "wb") as writer:
                    writer.write(b"changed and longer")
                return content

        def changing_open(path, *args, **kwargs):
            return ChangingReader(original_open(path, *args, **kwargs))

        with patch.object(Path, "open", changing_open):
            result = self.search()
        self.assertFalse(result["matches"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["skipped"]["changed"], 1)

    def test_supported_secrets_and_multiline_private_values_never_enter_previews(self):
        (self.policy.root / "credentials.txt").write_text(
            "password=canary-secret\nneedle safe\n-----BEGIN PRIVATE KEY-----\nPRIVATE-CANARY\n-----END PRIVATE KEY-----\n",
            encoding="utf-8")
        for query, expected_line in (("canary-secret", 1), ("needle", 2), ("PRIVATE-CANARY", 4)):
            with self.subTest(query=query):
                result = self.search(query)
                self.assertEqual(result["matches"][0]["line"], expected_line)
                self.assertNotIn("canary-secret", json.dumps(result))
                self.assertNotIn("PRIVATE-CANARY", json.dumps(result))

    def test_long_unicode_lines_respect_preview_and_serialized_output_limits(self):
        (self.policy.root / "long.txt").write_text(("needle" + "\u2603" * 300 + "\n") * 30, encoding="utf-8")
        result = self.search(limit=100)
        self.assertEqual(result["stop_reason"], "output_limit")
        self.assertFalse(result["complete"])
        self.assertLessEqual(len(json.dumps(result).encode("ascii")), result["limits"]["output_bytes"])
        self.assertTrue(all(len(m["text"]) <= 240 for m in result["matches"]))

    def test_match_limit_is_explicit(self):
        (self.policy.root / "lines.txt").write_text("needle\n" * 5, encoding="utf-8")
        result = self.search(limit=2)
        self.assertEqual(len(result["matches"]), 2)
        self.assertEqual(result["stop_reason"], "match_limit")
        self.assertFalse(result["complete"])

    def test_entry_file_byte_and_time_caps_stop_with_evidence(self):
        for index in range(3):
            (self.policy.root / f"file{index}.txt").write_text("eight123", encoding="utf-8")
        for constant, value, reason in (("MAX_ENTRIES", 1, "entry_limit"), ("MAX_FILES", 1, "file_limit"),
                                        ("MAX_BYTES", 10, "byte_limit")):
            with self.subTest(reason=reason), patch("local_agent.repository_search." + constant, value):
                result = self.search("absent")
                self.assertFalse(result["complete"])
                self.assertEqual(result["stop_reason"], reason)
        with patch("local_agent.repository_search.time.monotonic", side_effect=[0, 4]):
            result = self.search()
        self.assertEqual(result["stop_reason"], "time_limit")
        self.assertEqual(result["bytes_read"], 0)

    def test_oversized_unreadable_and_deep_inputs_are_explicitly_incomplete(self):
        target = self.policy.root / "file.txt"
        target.write_text("needle", encoding="utf-8")
        with patch("local_agent.repository_search.MAX_FILE", 2):
            result = self.search()
        self.assertEqual(result["skipped"]["oversized"], 1)
        self.assertFalse(result["complete"])
        with patch.object(Path, "open", side_effect=PermissionError("fixture")):
            result = self.search()
        self.assertEqual(result["skipped"]["unreadable"], 1)
        self.assertFalse(result["complete"])
        (self.policy.root / "deep").mkdir()
        (self.policy.root / "deep" / "inner").mkdir()
        with patch("local_agent.repository_search.MAX_DEPTH", 0):
            result = self.search()
        self.assertEqual(result["skipped"]["depth"], 1)
        self.assertFalse(result["complete"])

    def test_stop_and_invalid_input_fail_before_searching(self):
        for query in ("", "x" * 257, "two\nlines", "x\x00y"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                self.search(query)
        for limit in (0, 101, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.search(limit=limit)
        (self.policy.state / "STOP").touch()
        with self.assertRaises(Stopped):
            self.search()

    def test_profile_denial_and_schema_types_preserve_existing_boundaries(self):
        tools = Tools(self.policy, profile="browser")
        self.assertEqual(tools.execute("search_files", {"query": "needle"})["error"], "Denied")
        tools = Tools(self.policy, profile="coding")
        self.assertEqual(tools.execute("search_files", {"query": "needle", "limit": True})["error"], "TypeError")
        self.assertTrue(tools.execute("search_files", {"query": "needle"})["ok"])


class SearchAPITests(StudioAPIFixture, WorkspaceTest):
    def test_authentication_scope_and_results(self):
        (self.policy.root / "file.py").write_text("needle", encoding="utf-8")
        self.assertEqual(self.client.get("/search?query=needle").status_code, 401)
        result = self.client.get("/search", params={"query": "needle"}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["matches"][0]["line"], 1)
        self.assertEqual(self.client.get("/search", params={"query": "x", "project": ".."}, headers=self.headers).status_code, 403)

    def test_input_limits_and_stop_latch_are_explicit(self):
        for params in ({"query": ""}, {"query": "x" * 257}, {"query": "x", "limit": 101}):
            self.assertEqual(self.client.get("/search", params=params, headers=self.headers).status_code, 422)
        (self.policy.state / "STOP").touch()
        self.assertEqual(self.client.get("/search?query=x", headers=self.headers).status_code, 409)

    def test_secret_previews_are_sanitized_without_persisting_query_text(self):
        (self.policy.root / "file.py").write_text("password=search-canary", encoding="utf-8")
        response = self.client.get("/search", params={"query": "search-canary"}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["matches"])
        self.assertNotIn("search-canary", response.text)


class SearchProcessTests(StudioProcessFixture, WorkspaceTest):
    def test_agent_search_uses_selected_project_without_mutation_or_approval(self):
        for project in ("first", "second"):
            (self.policy.root / project).mkdir()
            (self.policy.root / project / "code.py").write_text("needle", encoding="utf-8")
        requests = self.requests

        class SearchProtocol(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                from .ollama_fixture import serve_metadata
                if not serve_metadata(self):
                    self.send_error(404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                from .ollama_fixture import serve_metadata
                if serve_metadata(self, body):
                    return
                requests.append(body)
                if body.get("format"):
                    message = {"content": '{"steps":["Search the project"]}'}
                elif any(m["role"] == "tool" for m in body["messages"]):
                    message = {"content": "Observed the search results"}
                else:
                    message = {"tool_calls": [{"function": {"name": "search_files", "arguments": {"query": "needle"}}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"message": {"role": "assistant", **message}, "done": True, "done_reason": "stop"}).encode())

        self.server.RequestHandlerClass = SearchProtocol
        task = self.manager.start(self.conversation, "Search project", "agent", "fixture", project="first", profile="coding")
        self.wait_until(lambda: not self.manager.running)
        events = [event for event in self.manager.store.events() if event["kind"] == "tool_result"]
        matches = events[0]["payload"]["result"]["untrusted_data"]["matches"]
        self.assertEqual([m["path"] for m in matches], ["code.py"])
        self.assertFalse(self.manager.pending())
        self.assertFalse(self.manager.store.verifications(task))
        self.assertEqual(self.manager.tasks()[0]["status"], "reported")
