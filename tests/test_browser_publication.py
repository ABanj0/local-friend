"""Opt-in local-only Playwright download publication; no public network required."""
import os
import unittest
from unittest.mock import patch

from local_agent.browser import Browser
from local_agent.file_ops import publish
from local_agent.safety import Denied

from .fixture_site import FixtureSite
from .support import WorkspaceTest


@unittest.skipUnless(os.getenv("LOCAL_AGENT_BROWSER_TEST") == "1", "Browser publication is opt-in")
class BrowserPublicationTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.site = self.enterContext(FixtureSite())
        self.config["browser"]["allowed_origins"].append(self.site.url)
        self.config["browser"]["channel"] = os.getenv("LOCAL_AGENT_BROWSER_CHANNEL", "msedge")
        self.browser = Browser(self.policy)
        self.addCleanup(self.browser.close)
        self.browser.open(self.site.url)

    def test_existing_and_pending_review_destinations_are_preserved(self):
        target = self.policy.root / "download.txt"
        target.write_text("existing")
        with self.assertRaises(Denied):
            self.browser.download("#download", "download.txt")
        self.assertEqual(target.read_text(), "existing")
        target.unlink()
        self.policy.approve = lambda *_: (target.write_text("concurrent") or True)
        with self.assertRaises(Denied):
            self.browser.download("#download", "download.txt")
        self.assertEqual(target.read_text(), "concurrent")

    def test_late_download_destination_wins_without_overwrite(self):
        target = self.policy.root / "download.txt"

        def race(policy, path, staged, *args):
            self.assertEqual(staged.read_text(), "local fixture download\n")
            target.write_text("late winner")
            return publish(policy, path, staged, *args)

        with patch("local_agent.browser.publish", race), self.assertRaises(Denied):
            self.browser.download("#download", "download.txt")
        self.assertEqual(target.read_text(), "late winner")
        self.assertEqual(list(self.policy.root.glob(".local-agent-*.tmp")), [])

    def test_download_is_published_once_with_no_temporary_hardlinks(self):
        result = self.browser.download("#download", "downloads/sample.txt")
        target = self.policy.root / "downloads/sample.txt"
        self.assertEqual(target.read_text(), "local fixture download\n")
        self.assertEqual(result["bytes"], target.stat().st_size)
        self.assertEqual(target.stat().st_nlink, 1)
        self.assertEqual(list(self.policy.root.rglob(".local-agent-*.tmp")), [])
