"""Multi-file review/conflict contracts; process inference replies are explicit fixtures."""
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler
from unittest.mock import Mock, patch

from local_agent.agent import Agent
from local_agent.coding import Coding
from local_agent.file_ops import atomic_write
from local_agent.safety import Denied, Stopped
from local_agent.tools import Tools

from .studio_support import StudioProcessFixture
from .support import WorkspaceTest
from .test_agent import call


class PatchSetTests(WorkspaceTest):
    def change(self, path, text):
        target = self.policy.root / path
        return {"path": path, "text": text,
                "expected_sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else "missing"}

    def pair(self):
        for path in ("first.txt", "second.txt"):
            (self.policy.root / path).write_bytes(b"original")
        return [self.change(path, "replacement") for path in ("first.txt", "second.txt")]

    def test_related_replace_and_create_share_one_review_and_exact_byte_evidence(self):
        (self.policy.root / "first.txt").write_bytes(b"original")
        result = Coding(self.policy).patch([self.change("first.txt", "replaced\r\n"),
                                          self.change("nested/new.txt", "snowman \u2603\n")])
        self.assertEqual(result["patch_status"], "applied")
        self.assertEqual(len(self.approvals), 1)
        action, details = self.approvals[0]
        self.assertEqual(action, "apply_patch_set")
        self.assertEqual([item["operation"] for item in details["files"]], ["replace", "create"])
        self.assertIn("No newline at end of file", details["files"][0]["diff"])
        self.assertEqual((self.policy.root / "first.txt").read_bytes(), b"replaced\r\n")
        self.assertEqual((self.policy.root / "nested/new.txt").read_bytes(), "snowman \u2603\n".encode())
        self.assertEqual([item["status"] for item in result["verifications"]], ["passed", "passed"])
        self.assertFalse(result["uncertain_paths"])
        self.assertFalse(result["pending_paths"])
        self.assertFalse(list(self.policy.root.rglob(".local-agent-*.tmp")))

    def test_read_hash_describes_raw_bytes_while_preserving_existing_newline_view(self):
        raw = b"first\r\nsecond\rthird\n"
        (self.policy.root / "file.txt").write_bytes(raw)
        result = Coding(self.policy).read("file.txt")
        self.assertEqual(result["text"], "first\nsecond\nthird\n")
        self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())

    def test_noop_set_requires_no_mutation_approval_and_preserves_identity(self):
        target = self.policy.root / "file.txt"
        target.write_bytes(b"unchanged")
        before = target.stat()
        result = Coding(self.policy).patch([self.change("file.txt", "unchanged")])
        self.assertEqual(result["patch_status"], "no_changes")
        self.assertFalse(self.approvals)
        self.assertFalse(result["written_paths"])
        self.assertEqual((target.stat().st_ino, target.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))
        self.assertEqual(result["verifications"][0]["status"], "passed")

    def test_stale_or_missing_expectation_denies_before_approval(self):
        changes = self.pair()
        for expected in ("0" * 64, "missing"):
            changes[1]["expected_sha256"] = expected
            with self.subTest(expected=expected), self.assertRaises(Denied):
                Coding(self.policy).patch(changes)
        self.assertFalse(self.approvals)
        self.assertEqual((self.policy.root / "first.txt").read_bytes(), b"original")

    def test_denied_set_preserves_all_files_and_does_not_create_directories(self):
        changes = self.pair() + [self.change("nested/new.txt", "new")]
        self.allow = False
        with self.assertRaises(Denied):
            Coding(self.policy).patch(changes)
        self.assertEqual((self.policy.root / "first.txt").read_bytes(), b"original")
        self.assertEqual((self.policy.root / "second.txt").read_bytes(), b"original")
        self.assertFalse((self.policy.root / "nested").exists())

    def test_changed_deleted_or_identically_recreated_later_file_blocks_entire_set(self):
        for mutation in ("edit", "delete", "replace"):
            changes = self.pair()
            target = self.policy.root / "second.txt"

            def approve(*_, mutation=mutation, target=target):
                if mutation == "edit":
                    target.write_bytes(b"concurrent")
                elif mutation == "delete":
                    target.unlink()
                else:
                    alternate = target.with_suffix(".replacement")
                    alternate.write_bytes(target.read_bytes())
                    os.replace(alternate, target)
                return True

            self.policy.approve = approve
            with self.subTest(mutation=mutation), self.assertRaisesRegex(Denied, "fresh review"):
                Coding(self.policy).patch(changes)
            self.assertEqual((self.policy.root / "first.txt").read_bytes(), b"original")
            if target.exists():
                self.assertEqual(target.read_bytes(), b"concurrent" if mutation == "edit" else b"original")

    def test_new_occupant_during_review_blocks_existing_file_too(self):
        changes = self.pair()[:1] + [self.change("new.txt", "proposal")]
        self.policy.approve = lambda *_: ((self.policy.root / "new.txt").write_bytes(b"winner") or True)
        with self.assertRaises(Denied):
            Coding(self.policy).patch(changes)
        self.assertEqual((self.policy.root / "first.txt").read_bytes(), b"original")
        self.assertEqual((self.policy.root / "new.txt").read_bytes(), b"winner")

    def test_path_aliases_overlap_controls_and_hardlinks_fail_without_review(self):
        changes = self.pair()
        for path in ("../outside.txt", "C:\\Windows\\file", ".env", ".git/config"):
            with self.subTest(path=path), self.assertRaises(Denied):
                Coding(self.policy).patch([dict(changes[0], path=path)])
        for other in ("FIRST.txt", "first.txt/child"):
            with self.subTest(other=other), self.assertRaises((ValueError, OSError)):
                Coding(self.policy).patch([changes[0], self.change(other, "new")])
        outside = self.policy.state / "private.txt"
        outside.write_bytes(b"outside")
        os.link(outside, self.policy.root / "alias.txt")
        with self.assertRaises(Denied):
            Coding(self.policy).patch([self.change("alias.txt", "new")])
        self.assertEqual(outside.read_bytes(), b"outside")
        self.assertFalse(self.approvals)

    def test_structural_semantic_and_size_limits_fail_without_dispatch_or_mutation(self):
        def forbidden(coding, changes: list):
            raise AssertionError("Must not dispatch")

        with patch.object(Coding, "patch", forbidden):
            # Construct a new registry after patching its trusted handler.
            tools = Tools(self.policy, profile="coding")
            for changes in ([], "[]", [{}], [{"path": "a", "expected_sha256": "missing", "text": 3}],
                            [{"path": "a", "expected_sha256": "missing", "text": "x", "delete": True}]):
                with self.subTest(changes=changes):
                    self.assertEqual(tools.execute("apply_patch", {"changes": changes})["error"], "TypeError")
            denied = Tools(self.policy, profile="browser").execute("apply_patch", {"changes": [self.change("a", "b")]})
            self.assertEqual(denied["error"], "Denied")
        for changes in ([self.change(f"{i}.txt", "x") for i in range(9)],
                        [self.change("large.txt", "x" * 64001)],
                        [dict(self.change("bad.txt", "x"), expected_sha256="NOT-A-HASH")]):
            with self.assertRaises((TypeError, ValueError)):
                Coding(self.policy).patch(changes)
        (self.policy.root / "large.txt").write_text("a" * 20_000, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "review exceeds"):
            Coding(self.policy).patch([self.change("large.txt", "b" * 20_000)])
        self.assertFalse(self.approvals)

    def test_review_redacts_whole_private_values_before_diff_and_copies_proposals(self):
        old = "password=OLD-CANARY\n-----BEGIN PRIVATE KEY-----\nOLD-PRIVATE-CANARY\n-----END PRIVATE KEY-----\n"
        new = old.replace("OLD", "NEW") + "changed\n"
        (self.policy.root / "file.txt").write_text(old, encoding="utf-8")
        changes = [self.change("file.txt", new)]

        def approve(action, details):
            self.assertTrue(details["files"][0]["redacted"])
            for value in ("OLD-CANARY", "NEW-CANARY", "OLD-PRIVATE-CANARY", "NEW-PRIVATE-CANARY"):
                self.assertNotIn(value, json.dumps(details))
            changes[0]["text"] = "callback altered proposal"
            return True

        self.policy.approve = approve
        result = Coding(self.policy).patch(changes)
        self.assertEqual((self.policy.root / "file.txt").read_text(encoding="utf-8"), new)
        self.assertNotIn("NEW-CANARY", json.dumps(result))

    def test_mid_publication_conflict_preserves_concurrent_edit_and_reports_prior_write(self):
        changes = self.pair()

        def publish(*args):
            atomic_write(*args)
            (self.policy.root / "second.txt").write_bytes(b"concurrent")

        with patch("local_agent.patches.atomic_write", side_effect=publish):
            result = Tools(self.policy).execute("apply_patch", {"changes": changes})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "PatchIncomplete")
        data = result["untrusted_data"]
        self.assertEqual(data["written_paths"], ["first.txt"])
        self.assertEqual(data["pending_paths"], ["second.txt"])
        self.assertEqual(data["verifications"][0]["status"], "passed")
        self.assertEqual((self.policy.root / "second.txt").read_bytes(), b"concurrent")

    def test_failure_after_publication_is_uncertain_and_does_not_blindly_roll_back(self):
        changes = self.pair()

        def fail_after_write(*args):
            atomic_write(*args)
            raise PermissionError("fixture private error")

        with patch("local_agent.patches.atomic_write", side_effect=fail_after_write):
            result = Coding(self.policy).patch(changes)
        self.assertEqual(result["patch_status"], "incomplete")
        self.assertEqual(result["uncertain_paths"], ["first.txt"])
        self.assertFalse(result["written_paths"])
        self.assertEqual(result["pending_paths"], ["second.txt"])
        self.assertEqual((self.policy.root / "first.txt").read_bytes(), b"replacement")
        self.assertEqual((self.policy.root / "second.txt").read_bytes(), b"original")
        self.assertNotIn("fixture private error", json.dumps(result))

    def test_bad_readback_blocks_later_files_and_agent_never_retries_incomplete_set(self):
        changes = self.pair()

        def wrong_write(policy, path, text, target, version):
            atomic_write(policy, path, "wrong bytes", target, version)

        model = Mock()
        model.chat.side_effect = [{"content": '{"steps":["Apply the reviewed set"]}'},
                                  call("apply_patch", {"changes": changes})]
        with patch("local_agent.patches.atomic_write", side_effect=wrong_write):
            result = Agent(model, Tools(self.policy), self.config["model"], lambda _: None).run("Edit related files")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(model.chat.call_count, 2)
        self.assertEqual(result["evidence"][0]["verifications"][0]["status"], "failed")
        self.assertEqual((self.policy.root / "second.txt").read_bytes(), b"original")

    def test_stop_after_first_write_never_applies_later_files_or_rolls_back(self):
        changes = self.pair()

        def stop_after_write(*args):
            atomic_write(*args)
            self.policy.stop_event.set()

        with patch("local_agent.patches.atomic_write", side_effect=stop_after_write), self.assertRaises(Stopped):
            Coding(self.policy).patch(changes)
        self.assertEqual((self.policy.root / "first.txt").read_bytes(), b"replacement")
        self.assertEqual((self.policy.root / "second.txt").read_bytes(), b"original")
        self.assertFalse(list(self.policy.root.rglob(".local-agent-*.tmp")))


class PatchSetProcessTests(StudioProcessFixture, WorkspaceTest):
    def scenario(self, decision):
        source = self.policy.root / "addition.py"
        source.write_text("def add(a,b):\n    return a-b\n", encoding="utf-8")
        changes = [{"path": "addition.py", "expected_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "text": "def add(a,b):\n    return a+b\n"},
                   {"path": "test_addition.py", "expected_sha256": "missing", "text":
                    "import unittest\nfrom addition import add\nclass Addition(unittest.TestCase):\n"
                    "    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"}]
        requests = self.requests

        class PatchProtocol(BaseHTTPRequestHandler):
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
                used = [m.get("tool_name") for m in body["messages"] if m["role"] == "tool"]
                if body.get("format"):
                    message = {"content": '{"steps":["Review related changes", "Run tests"]}'}
                elif "command" in used:
                    message = {"content": "Fixture observed file and test evidence"}
                elif "apply_patch" in used:
                    message = call("command", {"name": "test"})
                else:
                    message = call("apply_patch", {"changes": changes})
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"message": {"role": "assistant", **message}, "done": True, "done_reason": "stop"}).encode())

        self.server.RequestHandlerClass = PatchProtocol
        task = self.manager.start(self.conversation, "Apply related change and run tests", "agent", "fixture", profile="coding")
        self.wait_until(lambda: self.manager.pending())
        request = self.manager.pending()[0]
        self.assertEqual(request["action"], "apply_patch_set")
        self.assertEqual(len(request["details"]["files"]), 2)
        self.assertFalse((self.policy.root / "test_addition.py").exists())
        if decision == "conflict":
            source.write_text("concurrent edit", encoding="utf-8")
        self.manager.approve(task, request["id"], decision != "deny")
        if decision == "approve":
            self.wait_until(lambda: self.manager.pending())
            request = self.manager.pending()[0]
            self.assertEqual(request["action"], "execute_code")
            self.manager.approve(task, request["id"], True)
        self.wait_until(lambda: not self.manager.running)
        records = self.manager.store.verifications(task)
        if decision == "approve":
            self.assertEqual([record["kind"] for record in records], ["artifact", "artifact", "unittest"])
            self.assertTrue(all(record["status"] == "passed" for record in records))
            self.assertEqual(records[-1]["counts"]["tests_run"], 1)
            self.assertEqual(self.manager.tasks()[0]["status"], "reported")
        else:
            self.assertFalse(records)
            self.assertEqual(self.manager.tasks()[0]["status"], "blocked")
            self.assertFalse((self.policy.root / "test_addition.py").exists())
            self.assertEqual(source.read_text(), "concurrent edit" if decision == "conflict" else "def add(a,b):\n    return a-b\n")

    def test_real_worker_one_review_two_artifact_records_and_approved_tests(self):
        self.scenario("approve")

    def test_real_worker_denial_preserves_both_files(self):
        self.scenario("deny")

    def test_real_worker_changed_preimage_blocks_entire_set(self):
        self.scenario("conflict")
