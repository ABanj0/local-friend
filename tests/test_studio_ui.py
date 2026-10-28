"""Opt-in chat/attachment acceptance with actual backend and Ollama."""
import os
import unittest

from . import studio_ui_support as fixtures
from .support import WorkspaceTest


@unittest.skipUnless(os.getenv("LIVE_STUDIO_UI") == "1", "Set LIVE_STUDIO_UI=1 after building the frontend")
class StudioUITests(fixtures.StudioUIFixture, WorkspaceTest):
    def additional_ui_checks(self, page):
        from playwright.sync_api import expect
        requests = []
        page.on("request", lambda request: requests.append(request.post_data_json)
                if request.url.endswith("/slash") and request.method == "POST" else None)
        page.get_by_role("button", name="Agent", exact=True).click()
        profile = page.get_by_role("combobox", name="Tool access")
        expect(profile).to_have_value("unified")
        profile.select_option("browser")
        page.get_by_role("textbox", name="Message", exact=True).fill("/test")
        page.get_by_title("Send message", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("requires a profile with coding tools")
        self.assertEqual(requests[-1]["profile"], "browser")
        profile.select_option("unified")
        page.get_by_title("Dismiss notification").click()
        page.get_by_role("button", name="Chat", exact=True).click()

    def test_chat_attachment_management(self):
        self.run_chat_attachment_management()
