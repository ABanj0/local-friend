import hashlib
import json
import os
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.review import fingerprint
from local_agent.safety import Denied
from local_agent.studio.store import Store
from local_agent.verification import observe_artifact, validate

from .studio_support import StudioAPIFixture, StudioProcessFixture
from .support import WorkspaceTest


class ArtifactVerificationTests(WorkspaceTest):
    def test_new_unicode_empty_and_noop_readbacks_match_exact_bytes(self):
        coding = Coding(self.policy)
        for name, text in (("unicode.txt", "Snowman: \u2603\r\n"), ("empty.txt", "")):
            with self.subTest(name=name):
                first = coding.write(name, text)
                before = (self.policy.root / name).stat()
                second = coding.write(name, text)
                for result in (first, second):
                    observed = result["verification"]
                    self.assertEqual(observed["kind"], "artifact")
                    self.assertEqual(observed["status"], "passed")
                    self.assertEqual(observed["observed_bytes"], len(text.encode()))
                    self.assertEqual(observed["observed_sha256"], hashlib.sha256(text.encode()).hexdigest())
                self.assertFalse(second["changed"])
                self.assertEqual((self.policy.root / name).stat().st_mtime_ns, before.st_mtime_ns)
                self.assertNotEqual(first["verification"]["id"], second["verification"]["id"])

    def test_line_endings_require_review_when_bytes_differ(self):
        target = self.policy.root / "lines.txt"
        target.write_bytes(b"line\r\n")
        result = Coding(self.policy).write("lines.txt", "line\n")
        self.assertEqual(self.approvals[0][0], "overwrite_file")
        self.assertIn("\r\n", self.approvals[0][1]["diff"])
        self.assertEqual(target.read_bytes(), b"line\n")
        self.assertEqual(result["verification"]["status"], "passed")

    def test_mismatched_publication_is_failed_and_never_repaired(self):
        target = self.policy.root / "file.txt"
        with patch("local_agent.coding.atomic_write", side_effect=lambda *args: target.write_bytes(b"other")) as publish:
            result = Coding(self.policy).write("file.txt", "expected")
        self.assertEqual(result["verification"]["status"], "failed")
        self.assertEqual(result["verification"]["reason"], "content_mismatch")
        self.assertEqual(target.read_bytes(), b"other")
        self.assertEqual(publish.call_count, 1)

    def test_missing_publication_never_claims_an_artifact_exists(self):
        with patch("local_agent.coding.atomic_write"):
            result = Coding(self.policy).write("file.txt", "expected")
        self.assertEqual(result["verification"]["status"], "failed")
        self.assertEqual(result["verification"]["reason"], "missing_artifact")
        self.assertIsNone(result["bytes"])

    def test_concurrent_change_after_first_read_is_inconclusive(self):
        target = self.policy.root / "file.txt"
        calls = []

        def changed(path, limit):
            version = fingerprint(path, limit)
            calls.append(version)
            if len(calls) == 1:
                target.write_bytes(b"later")
            return version

        with patch("local_agent.verification.fingerprint", side_effect=changed):
            result = Coding(self.policy).write("file.txt", "expected")
        self.assertEqual(result["verification"]["status"], "inconclusive")
        self.assertEqual(target.read_bytes(), b"later")
        self.assertIsNone(result["verification"]["observed_sha256"])

    def test_hardlink_replacement_is_not_read_or_modified(self):
        outside = self.policy.state / "outside.txt"
        outside.write_bytes(b"private outside data")
        target = self.policy.root / "file.txt"
        with (patch("local_agent.coding.atomic_write", side_effect=lambda *args: os.link(outside, target)),
              patch("local_agent.verification.fingerprint", side_effect=AssertionError("Must not read linked bytes"))):
            result = Coding(self.policy).write("file.txt", "expected")
        self.assertEqual(result["verification"]["status"], "inconclusive")
        self.assertEqual(outside.read_bytes(), b"private outside data")

    def test_outside_destination_and_path_are_never_read(self):
        outside = self.policy.state / "outside.txt"
        outside.write_bytes(b"outside")
        with self.assertRaises(Denied):
            observe_artifact(self.policy, "file.txt", b"outside", outside)
        result = observe_artifact(self.policy, "../state/outside.txt", b"outside", self.policy.root / "file.txt")
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["observed_sha256"])

    def test_denied_overwrite_does_not_write_or_verify(self):
        target = self.policy.root / "file.txt"
        target.write_bytes(b"original")
        self.allow = False
        with patch("local_agent.coding.observe_artifact") as observer, self.assertRaises(Denied):
            Coding(self.policy).write("file.txt", "replacement")
        observer.assert_not_called()
        self.assertEqual(target.read_bytes(), b"original")

    def test_invalid_metadata_and_claimed_pass_cannot_override_hash_mismatch(self):
        result = Coding(self.policy).write("file.txt", "expected")["verification"]
        self.assertEqual(validate({**result, "status": "failed"})["status"], "passed")
        self.assertEqual(validate({**result, "observed_sha256": "0" * 64, "status": "passed"})["status"], "failed")
        for changes in ({"observed_bytes": True}, {"path": "../outside"}, {"version": True},
                        {"expected_sha256": "bad"}, {"resource_version": None}, {"observation": "invented"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate({**result, **changes})

    def test_records_contain_no_file_contents_and_redact_sensitive_labels(self):
        result = Coding(self.policy).write("password=artifact-canary.txt", "UNLABELED_PRIVATE_CONTENT")["verification"]
        self.assertNotIn("artifact-canary", json.dumps(result))
        self.assertNotIn("UNLABELED_PRIVATE_CONTENT", json.dumps(result))
        store = Store(self.policy.state / "artifact.sqlite3")
        conversation = store.conversation()
        task = store.task(conversation, "agent", "fixture")
        store.verification(task, result)
        store.complete(task, {"status": "reported", "report": "Observed write"})
        reopened = Store(store.path)
        self.assertEqual(reopened.verifications(task)[0]["observed_sha256"], result["observed_sha256"])
        self.assertNotIn("UNLABELED_PRIVATE_CONTENT", json.dumps(reopened.events()))


class ArtifactProcessTests(StudioProcessFixture, WorkspaceTest):
    def test_reviewed_creation_persists_readback_separately_from_model_report(self):
        task = self.manager.start(self.conversation, "Create the fixture file", "agent", "fixture", profile="coding")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.assertFalse(self.manager.store.verifications(task))
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: not self.manager.running)
        checks = self.manager.store.verifications(task)
        self.assertEqual(checks[0]["status"], "passed")
        self.assertEqual(checks[0]["kind"], "artifact")
        self.assertEqual(checks[0]["expected_sha256"], hashlib.sha256(b"reviewed").hexdigest())
        self.assertEqual((self.policy.root / "review.txt").read_bytes(), b"reviewed")
        self.assertEqual(sum(event["kind"] == "verification" for event in self.manager.store.events()), 1)

    def test_denied_creation_has_no_artifact_evidence(self):
        task = self.manager.start(self.conversation, "Create the fixture file", "agent", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        self.manager.approve(task, self.manager.pending()[0]["id"], False)
        self.wait_until(lambda: not self.manager.running)
        self.assertFalse(self.manager.store.verifications(task))
        self.assertFalse((self.policy.root / "review.txt").exists())


class ArtifactAPITests(StudioAPIFixture, WorkspaceTest):
    def test_authenticated_readback_history_survives_completion_and_cascades_on_delete(self):
        store = self.client.app.state.manager.store
        conversation = store.conversation()
        task = store.task(conversation, "agent", "fixture")
        check = Coding(self.policy).write("api.txt", "reviewed")["verification"]
        store.verification(task, check)
        store.complete(task, {"status": "reported", "report": "Observed artifact"})
        self.assertEqual(self.client.get(f"/tasks/{task}/verifications").status_code, 401)
        checks = self.client.get(f"/tasks/{task}/verifications", headers=self.headers).json()
        self.assertEqual(checks[0]["observed_sha256"], hashlib.sha256(b"reviewed").hexdigest())
        store.delete_conversation(conversation)
        self.assertFalse(store.verifications(task))
