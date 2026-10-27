"""Opt-in real integration checks; no unavailable capability is silently marked passed."""
import base64
import json
import os
import struct
import unittest
import zlib

from local_agent.agent import Agent
from local_agent.browser import Browser
from local_agent.model import Ollama
from local_agent.tools import Tools

from .fixture_site import FixtureSite, Handler
from .support import WorkspaceTest


@unittest.skipUnless(os.getenv("LOCAL_AGENT_BROWSER_TEST") == "1", "Browser integration is opt-in")
class LiveBrowserTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.config["browser"]["channel"] = os.getenv("LOCAL_AGENT_BROWSER_CHANNEL", "")
        self.browser = Browser(self.policy)
        self.addCleanup(self.browser.close)

    def test_browser_fixture_navigation_form_tabs_download(self):
        with FixtureSite() as site:
            self.config["browser"]["allowed_origins"].append(site.url)
            first = self.browser.open(site.url)
            self.assertIn("Local Agent Test", first["text"])
            self.browser.fill("#name", "Harmless local sample")
            self.assertEqual(self.browser.page("main").locator("#name").input_value(), "Harmless local sample")
            self.browser.click("#next")
            self.assertIn("Second page verified", self.browser.read()["text"])
            self.browser.open(site.url, "other")
            self.assertEqual(len(self.browser.pages), 2)
            self.browser.download("#download", "downloads/sample.txt", "other")
            self.assertEqual((self.policy.root / "downloads/sample.txt").read_text(), "local fixture download\n")
            from pathlib import Path
            screenshot = self.browser.screenshot()
            self.assertTrue(Path(screenshot["image_path"]).read_bytes().startswith(b"\x89PNG"))
            self.assertEqual(Handler.submissions, 0)

    def test_external_post_is_denied(self):
        with FixtureSite() as site:
            self.config["browser"]["allowed_origins"].append(site.url)
            self.browser.open(site.url)
            self.policy.approve = lambda action, details: action == "browser_click"
            self.browser.click("#submit")
            self.browser.page("main").wait_for_timeout(100)
            self.assertEqual(Handler.submissions, 0)

    def test_public_websites(self):
        from playwright.sync_api import expect

        # Use a maintained testing demo, not example.com's changeable documentation page.
        # Never approve a network mutation, even if the demo changes its input behavior.
        self.policy.approve = lambda action, details: action in {"browser_click", "browser_fill"}
        self.browser.start()
        mutations = []
        self.browser.context.on("request", lambda request: mutations.append(request.method)
                                if request.method not in {"GET", "HEAD", "OPTIONS"} else None)
        url = "https://demo.playwright.dev/todomvc/"
        self.browser.open(url)
        page = self.browser.page("main")
        expect(page.locator("h1")).to_have_text("todos")
        self.assertIn("todos", self.browser.read()["text"].lower())

        # Exercise public app-route navigation and a second isolated tab without submitting.
        navigated = self.browser.open(url + "#/active")
        self.assertEqual(navigated["url"], url + "#/active")
        expect(page.locator("h1")).to_have_text("todos")
        self.browser.open(url, "public")
        self.browser.fill(".new-todo", "Harmless draft; do not submit", "public")
        draft = self.browser.page("public")
        expect(draft.locator(".new-todo")).to_have_value("Harmless draft; do not submit")
        expect(draft.locator(".todo-list li")).to_have_count(0)
        self.assertEqual(len(self.browser.pages), 2)
        self.assertEqual(mutations, [], "Public demo attempted an external submission")

    def test_browser_to_file_dispatch(self):
        # Deterministic integration, explicitly not a live LLM test.
        with FixtureSite() as site:
            self.config["browser"]["allowed_origins"].append(site.url)
            tools = Tools(self.policy)
            self.addCleanup(tools.close)
            page = tools.execute("browser_open", {"url": site.url})
            self.assertTrue(page["ok"], page)
            output = tools.execute("write_file", {"path": "page.txt", "text": page["untrusted_data"]["text"]})
            self.assertTrue(output["ok"], output)
            readback = tools.execute("read_file", {"path": "page.txt"})
            self.assertIn("Local Agent Test", readback["untrusted_data"]["text"])


@unittest.skipUnless(os.getenv("LOCAL_AGENT_MODEL_TEST") == "1", "Live Ollama tests are opt-in")
class LiveModelTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.model = Ollama(self.config["model"])

    def test_model_structured_output_and_gpu(self):
        schema = {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]}
        reply = self.model.chat([{"role": "user", "content": "Return JSON with value equal to 42."}], schema=schema)
        self.assertEqual(json.loads(reply["content"])["value"], 42)
        running = self.model.request("/api/ps")["models"]
        chosen = [item for item in running if item["name"] == self.config["model"]["name"]]
        self.assertTrue(chosen, running)
        self.assertGreater(chosen[0]["size_vram"], 0)
        print("GPU evidence:", json.dumps(chosen[0]))

    def test_real_tool_call_and_result(self):
        tools = Tools(self.policy)
        schema = [tool for tool in tools.schemas if tool["function"]["name"] == "write_file"]
        messages = [{"role": "user", "content": "Use write_file to create probe.txt containing exactly tool-call-verified."}]
        response = self.model.chat(messages, tools=schema)
        calls = response.get("tool_calls", [])
        self.assertTrue(calls, response)
        function = calls[0]["function"]
        self.assertEqual(function["name"], "write_file")
        self.assertEqual(function["arguments"]["path"], "probe.txt")
        result = tools.execute(function["name"], function["arguments"])
        self.assertTrue(result["ok"], result)
        self.assertEqual((self.policy.root / "probe.txt").read_text().strip(), "tool-call-verified")
        messages += [response, {"role": "tool", "tool_name": "write_file", "content": json.dumps(result)}]
        followup = self.model.chat(messages)
        self.assertTrue(followup.get("content"))

    def test_vision(self):
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 32, 32, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress((b"\x00" + b"\xff\x00\x00" * 32) * 32)) + chunk(b"IEND", b"")
        reply = self.model.chat([{"role": "user", "content": "What is the predominant color? Answer one color word.",
                                 "images": [base64.b64encode(png).decode()]}])
        self.assertIn("red", reply["content"].lower())

    @unittest.skipUnless(os.getenv("LOCAL_AGENT_BROWSER_TEST") == "1", "Also requires browser integration")
    def test_unified_live_model_browser_and_files(self):
        self.config["browser"]["channel"] = os.getenv("LOCAL_AGENT_BROWSER_CHANNEL", "")
        with FixtureSite() as site:
            self.config["browser"]["allowed_origins"].append(site.url)
            tools = Tools(self.policy)
            self.addCleanup(tools.close)
            result = Agent(self.model, tools, self.config["model"]).run(
                f"Open {site.url} with browser_open, read its title, write only that title to title.txt, "
                "read the file back to verify it, and report the result. Do not click or submit anything.")
            self.assertEqual(result["status"], "reported", result)
            self.assertEqual((self.policy.root / "title.txt").read_text().strip(), "Agent fixture")
            names = {event["tool"] for event in result["evidence"] if event["ok"]}
            self.assertTrue({"browser_open", "write_file", "read_file"} <= names)


@unittest.skipUnless(os.getenv("LOCAL_AGENT_DESKTOP_TEST") == "1", "Desktop test moves focus; opt-in")
class LiveDesktopTests(WorkspaceTest):
    def test_notepad_write_save_readback(self):
        import time

        from local_agent.desktop import Desktop
        desktop = Desktop(self.policy)
        desktop.launch("notepad")
        desktop.input("notepad", "text", text="Local agent Notepad validation.")
        desktop.input("notepad", "hotkey", keys="ctrl+shift+s")
        time.sleep(1)
        destination = self.policy.path("notepad-test.txt")
        desktop.input("notepad", "text", text=str(destination))
        desktop.input("notepad", "hotkey", keys="enter")
        deadline = time.monotonic() + 10
        while not destination.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertTrue(destination.exists(), "Notepad save dialog did not create expected file")
        self.assertIn("Local agent Notepad validation.", destination.read_text(encoding="utf-8-sig"))
