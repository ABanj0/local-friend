"""Real atomic/exclusive filesystem publication and denied Git helper execution."""
import ctypes
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from local_agent.coding import Coding
from local_agent.process import run_process
from local_agent.safety import Denied

from .support import WorkspaceTest


class PublicationTests(WorkspaceTest):
    def test_failure_before_publish_leaves_old_content_and_no_staging_file(self):
        coding = Coding(self.policy)
        coding.write("file.txt", "original")
        with (patch("local_agent.file_ops.publish", side_effect=OSError("injected publication failure")),
              self.assertRaises(OSError)):
            coding.write("file.txt", "replacement")
        self.assertEqual((self.policy.root / "file.txt").read_text(), "original")
        self.assertEqual(list(self.policy.root.glob(".local-agent-*.tmp")), [])

    def test_exclusive_publication_never_replaces_a_late_winner(self):
        target = self.policy.root / "file.txt"
        real_link = os.link

        def race(source, destination, **kwargs):
            target.write_text("concurrent winner")
            return real_link(source, destination, **kwargs)

        with patch("local_agent.file_ops.os.link", race), self.assertRaisesRegex(Denied, "fresh review"):
            Coding(self.policy).write("file.txt", "agent proposal")
        self.assertEqual(target.read_text(), "concurrent winner")
        self.assertEqual(list(self.policy.root.glob(".local-agent-*.tmp")), [])

    def test_atomic_write_is_complete_utf8_and_replaces_shorter_content(self):
        coding = Coding(self.policy)
        coding.write("nested/file.txt", "long original text")
        coding.write("nested/file.txt", "\u03bb\n")
        self.assertEqual((self.policy.root / "nested/file.txt").read_bytes(), "\u03bb\n".encode())
        self.assertEqual(list(self.policy.root.rglob(".local-agent-*.tmp")), [])

    @unittest.skipUnless(os.name == "nt", "Windows DACL retention check")
    def test_windows_replacement_preserves_dacl(self):
        from ctypes import wintypes
        api = ctypes.WinDLL("advapi32", use_last_error=True)
        api.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                                        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        api.GetFileSecurityW.restype = wintypes.BOOL
        api.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
                                                ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
        api.GetSecurityDescriptorDacl.restype = wintypes.BOOL
        api.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
        api.SetFileSecurityW.restype = wintypes.BOOL

        def dacl(path):
            needed = wintypes.DWORD()
            api.GetFileSecurityW(str(path), 4, None, 0, ctypes.byref(needed))
            if not needed.value:
                raise ctypes.WinError(ctypes.get_last_error())
            output = ctypes.create_string_buffer(needed.value)
            if not api.GetFileSecurityW(str(path), 4, output, needed, ctypes.byref(needed)):
                raise ctypes.WinError(ctypes.get_last_error())
            present, defaulted, acl = wintypes.BOOL(), wintypes.BOOL(), ctypes.c_void_p()
            if not api.GetSecurityDescriptorDacl(output, ctypes.byref(present), ctypes.byref(acl),
                                                ctypes.byref(defaulted)):
                raise ctypes.WinError(ctypes.get_last_error())
            # Compare actual ACL and protection; ReplaceFileW may set AUTO_INHERITED
            # in the descriptor without changing any access-control entry.
            length = ctypes.c_ushort.from_address(acl.value + 2).value if acl.value else 0
            return (bool(present), bool(defaulted), ctypes.string_at(acl, length) if acl.value else None,
                    int.from_bytes(output.raw[2:4], "little") & 0x1000)

        coding = Coding(self.policy)
        coding.write("file.txt", "old")
        target = self.policy.root / "file.txt"
        for protected in (False, True):
            with self.subTest(protected=protected):
                if protected:
                    needed = wintypes.DWORD()
                    api.GetFileSecurityW(str(target), 4, None, 0, ctypes.byref(needed))
                    descriptor = ctypes.create_string_buffer(needed.value)
                    self.assertTrue(api.GetFileSecurityW(str(target), 4, descriptor, needed, ctypes.byref(needed)))
                    self.assertTrue(api.SetFileSecurityW(str(target), 4 | 0x80000000, descriptor))
                before = dacl(target)
                coding.write("file.txt", "new " + str(protected))
                self.assertEqual(dacl(target), before)

    @unittest.skipUnless(os.name == "nt", "Windows junction defense")
    def test_junction_write_is_refused(self):
        actual = self.policy.root / "actual"
        actual.mkdir()
        alias = self.policy.root / "alias"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(actual)],
                                check=False, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaises(Denied):
            Coding(self.policy).write("alias/file.txt", "must not appear")
        self.assertFalse((actual / "file.txt").exists())

    def test_hardlink_created_during_review_is_refused(self):
        target = self.policy.root / "file.txt"
        target.write_text("original")
        alias = self.policy.root / "alias.txt"
        self.policy.approve = lambda *_: (alias.hardlink_to(target) or True)
        with self.assertRaises(Denied):
            Coding(self.policy).write("file.txt", "replacement")
        self.assertEqual(alias.read_text(), "original")

    def test_staging_file_symlink_is_rejected_without_publication(self):
        target = self.policy.root / "new.txt"
        # Reparse flag defense without requiring symlink privileges on CI.
        original = self.policy.no_links

        def deny_stage(path):
            if path.name.startswith(".local-agent-"):
                raise Denied("Injected reparse point")
            return original(path)

        with patch.object(self.policy, "no_links", deny_stage), self.assertRaises(Denied):
            Coding(self.policy).write("new.txt", "proposal")
        self.assertFalse(target.exists())


class GitHelperTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        if not shutil.which("git"):
            self.skipTest("Git unavailable")
        self.coding = Coding(self.policy)
        self.git("init")
        self.git("config", "user.name", "Helper Test")
        self.git("config", "user.email", "helper@example.invalid")
        (self.policy.root / "sample.txt").write_text("sample")
        self.git("add", "sample.txt")
        self.marker = self.policy.root / "HELPER-MUST-NOT-RUN"
        helper = self.policy.root / "helper.py"
        helper.write_text("from pathlib import Path\nPath(" + repr(str(self.marker)) + ").touch()\n")
        self.command = f"'{Path(sys.executable).as_posix()}' '{helper.as_posix()}'"

    def git(self, *args):
        result = run_process([shutil.which("git"), *args], self.policy.root, self.policy)
        self.assertEqual(result["exit_code"], 0, result)
        return result

    def test_clean_process_and_textconv_helpers_never_execute(self):
        for key in ("filter.trap.clean", "filter.trap.process", "diff.trap.textconv"):
            with self.subTest(key=key):
                self.git("config", key, self.command)
                (self.policy.root / ".gitattributes").write_text("*.txt filter=trap diff=trap\n")
                for action in ("stage", "diff", "status"):
                    with self.assertRaises(Denied):
                        self.coding.git(action, path="sample.txt")
                self.assertFalse(self.marker.exists())
                self.git("config", "--unset", key)

    def test_signing_program_and_includes_are_denied(self):
        self.git("config", "gpg.program", self.command)
        self.git("config", "commit.gpgsign", "true")
        with self.assertRaises(Denied):
            self.coding.git("commit", message="Must not execute signing helper")
        self.assertFalse(self.marker.exists())
        self.git("config", "--unset", "gpg.program")
        include = self.policy.root / "extra.config"
        include.write_text('[filter "trap"]\n\tclean = ' + self.command + '\n')
        self.git("config", "include.path", str(include))
        with self.assertRaises(Denied):
            self.coding.git("status")
        self.assertFalse(self.marker.exists())

    def test_helper_added_while_approval_pending_blocks_operation(self):
        def approve(*_):
            self.git("config", "filter.trap.clean", self.command)
            (self.policy.root / ".gitattributes").write_text("*.txt filter=trap\n")
            return True

        self.policy.approve = approve
        with self.assertRaises(Denied):
            self.coding.git("stage", path="sample.txt")
        self.assertFalse(self.marker.exists())

    def test_hooks_are_overridden_and_normal_commit_still_works(self):
        hooks = self.policy.root / ".git/hooks"
        (hooks / "pre-commit").write_text("#!/bin/sh\n" + self.command + "\n")
        result = self.coding.git("commit", message="Approved unsigned fixture commit")
        self.assertEqual(result["exit_code"], 0, result)
        self.assertFalse(self.marker.exists())

    def test_external_worktree_cannot_widen_read_scope(self):
        outside = Path(self.temp.name) / "outside-worktree"
        outside.mkdir()
        (outside / "private.txt").write_text("PRIVATE-OUTSIDE-SCOPE")
        self.git("config", "core.worktree", str(outside))
        for action in ("status", "diff", "log"):
            with self.subTest(action=action), self.assertRaises(Denied):
                self.coding.git(action)
