"""Pending-review conflicts with real files, index swaps and disposable Git repositories."""
import os
import shutil
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.file_ops import publish
from local_agent.process import run_process
from local_agent.review import fingerprint
from local_agent.safety import Denied
from local_agent.tools import Tools

from .support import WorkspaceTest


class ReviewTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.coding = Coding(self.policy)

    def raw_git(self, *args):
        result = run_process([shutil.which("git"), *args], self.policy.root, self.policy)
        self.assertEqual(result["exit_code"], 0, result)
        return result["output"].strip()

    def repository(self, committed=False):
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        self.raw_git("init")
        self.raw_git("config", "user.name", "Review Test")
        self.raw_git("config", "user.email", "review@example.invalid")
        self.coding.write("sample.txt", "reviewed original\n")
        self.raw_git("add", "sample.txt")
        if committed:
            self.raw_git("commit", "-m", "Initial fixture")
            self.coding.write("sample.txt", "proposed second version\n")
            self.raw_git("add", "sample.txt")

    def test_changed_deleted_or_recreated_preimage_is_not_overwritten(self):
        target = self.policy.root / "file.txt"
        for mutation in ("edit", "delete", "replace"):
            with self.subTest(mutation=mutation):
                target.write_text("original", encoding="utf-8")
                timestamp = target.stat().st_mtime_ns

                def approve(action, details, mutation=mutation, timestamp=timestamp):
                    self.assertEqual(action, "overwrite_file")
                    self.assertEqual(len(details["preimage_sha256"]), 64)
                    if mutation == "edit":
                        target.write_text("modified", encoding="utf-8")
                        os.utime(target, ns=(timestamp, timestamp))
                    elif mutation == "delete":
                        target.unlink()
                    else:
                        alternate = target.with_suffix(".replacement")
                        alternate.write_bytes(target.read_bytes())
                        os.replace(alternate, target)
                    return True

                self.policy.approve = approve
                with self.assertRaisesRegex(Denied, "fresh review"):
                    self.coding.write("file.txt", "agent proposal")
                self.assertEqual(target.read_text() if target.exists() else None,
                                 None if mutation == "delete" else "modified" if mutation == "edit" else "original")

    def test_fresh_review_after_conflict_succeeds(self):
        target = self.policy.root / "file.txt"
        target.write_text("first")
        self.policy.approve = lambda *_: (target.write_text("concurrent") or True)
        with self.assertRaises(Denied):
            self.coding.write("file.txt", "proposal")
        self.policy.approve = lambda *_: True
        self.coding.write("file.txt", "proposal")
        self.assertEqual(target.read_text(), "proposal")

    def test_studio_create_review_cannot_overwrite_a_new_occupant(self):
        target = self.policy.root / "new.txt"
        self.coding.review_create = True
        self.policy.approve = lambda *_: (target.write_text("concurrent") or True)
        with self.assertRaisesRegex(Denied, "fresh review"):
            self.coding.write("new.txt", "proposal")
        self.assertEqual(target.read_text(), "concurrent")

    def test_last_moment_path_swap_does_not_truncate_replacement(self):
        target = self.policy.root / "file.txt"
        target.write_text("original")
        def swapped(*args):
            alternate = target.with_suffix(".replacement")
            alternate.write_text("new occupant")
            os.replace(alternate, target)
            return publish(*args)

        with patch("local_agent.file_ops.publish", swapped), self.assertRaises(Denied):
            self.coding.write("file.txt", "proposal")
        self.assertEqual(target.read_text(), "new occupant")

    def test_unchanged_preimage_noop_and_schema_are_preserved(self):
        self.coding.write("file.txt", "original")
        self.assertFalse(self.coding.write("file.txt", "original")["changed"])
        self.assertEqual(self.approvals, [])
        self.coding.write("file.txt", "new")
        self.assertEqual(len(self.approvals), 1)
        schema = next(item["function"] for item in Tools(self.policy).schemas
                      if item["function"]["name"] == "write_file")
        self.assertEqual(set(schema["parameters"]["properties"]), {"path", "text"})

    def test_commit_rejects_changed_index_after_approval(self):
        self.repository()

        def approve(action, details):
            self.assertEqual(action, "git_commit")
            self.assertIn("reviewed original", details["staged_diff"]["output"])
            (self.policy.root / "sample.txt").write_text("concurrent staged content")
            self.raw_git("add", "sample.txt")
            return True

        self.policy.approve = approve
        with self.assertRaisesRegex(Denied, "fresh review"):
            self.coding.git("commit", message="Must not commit")
        result = run_process([shutil.which("git"), "rev-parse", "--verify", "HEAD"],
                             self.policy.root, self.policy)
        self.assertNotEqual(result["exit_code"], 0)
        self.assertIn("concurrent staged content", self.raw_git("diff", "--cached"))

    def test_commit_rejects_identical_index_replacement(self):
        self.repository()
        index = self.policy.root / ".git/index"

        def approve(*_):
            alternate = index.with_suffix(".replacement")
            alternate.write_bytes(index.read_bytes())
            os.replace(alternate, index)
            return True

        self.policy.approve = approve
        with self.assertRaisesRegex(Denied, "fresh review"):
            self.coding.git("commit", message="Must not commit")

    def test_commit_rejects_changed_head_tree_or_branch(self):
        self.repository(committed=True)
        original = self.raw_git("rev-parse", "HEAD")

        def approve(*_):
            self.raw_git("commit", "-m", "Concurrent user commit")
            return True

        self.policy.approve = approve
        with self.assertRaisesRegex(Denied, "fresh review"):
            self.coding.git("commit", message="Must not commit")
        self.assertNotEqual(self.raw_git("rev-parse", "HEAD"), original)
        self.assertEqual(self.raw_git("rev-list", "--count", "HEAD"), "2")

    def test_stage_rejects_file_changed_during_review(self):
        self.repository()
        original_index = fingerprint(self.policy.root / ".git/index")
        self.policy.approve = lambda *_: ((self.policy.root / "sample.txt").write_text("changed") or True)
        with self.assertRaisesRegex(Denied, "fresh review"):
            self.coding.git("stage", path="sample.txt")
        self.assertEqual(fingerprint(self.policy.root / ".git/index"), original_index)

    def test_denying_review_leaves_file_and_index_intact(self):
        self.repository()
        index = fingerprint(self.policy.root / ".git/index")
        self.allow = False
        for action in ("stage", "commit"):
            with self.subTest(action=action), self.assertRaises(Denied):
                self.coding.git(action, message="Denied", path="sample.txt")
        self.assertEqual(fingerprint(self.policy.root / ".git/index"), index)
