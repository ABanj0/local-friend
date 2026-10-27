import base64
import copy
import io
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from local_agent.agent import Agent
from local_agent.browser import Browser
from local_agent.captures import Captures
from local_agent.model import Ollama
from local_agent.safety import Denied
from local_agent.studio.attachments import parse_attachment
from local_agent.studio.manager import Manager
from local_agent.tools import Tools
from local_agent.vision import VisualContext

from .fixture_site import FixtureSite
from .studio_support import StudioProcessFixture
from .support import WorkspaceTest
from .test_agent import call


def png(color="blue", size=(32, 32)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


class VisionTests(WorkspaceTest):
    def test_agent_retains_originals_and_only_latest_observation(self):
        with patch.object(Browser, "screenshot", lambda browser, tab="main": {
                "image_path": tools.captures.write(png())}):
            tools = Tools(self.policy)
        self.addCleanup(tools.close)
        original = {"role": "user", "content": "Compare", "images": [base64.b64encode(png("red")).decode()]}
        before = copy.deepcopy(original)
        snapshots = []
        replies = iter([{"content": '{"steps":["Observe twice"]}'},
                        call("browser_screenshot", {}), call("browser_screenshot", {}),
                        {"content": "Compared"}])

        def chat(messages, **kwargs):
            snapshots.append(copy.deepcopy(messages))
            return next(replies)

        result = Agent(Mock(chat=chat), tools, self.config["model"], lambda _: None).run(
            "Compare", user_message=original)
        self.assertEqual(result["status"], "reported")
        self.assertEqual(original, before)
        for messages in snapshots[-2:]:
            images = [image for message in messages for image in message.get("images", [])]
            self.assertEqual(len(images), 2)
            self.assertEqual(images[0], original["images"][0])
            self.assertEqual(messages[-2]["role"], "tool")
            self.assertEqual(messages[-1]["role"], "user")
        self.assertFalse(list(tools.captures.path.glob("*.png")))

    def test_image_budget_preserves_eight_originals(self):
        messages = [{"role": "user", "images": ["original"] * 8}]
        context = VisualContext(messages)
        self.assertIn("omitted", context.observe(png()))
        self.assertEqual(messages[0]["images"], ["original"] * 8)
        with self.assertRaises(ValueError):
            VisualContext([{"images": ["original"] * 9}])

    def test_observation_size_and_invalid_replacement(self):
        messages = []
        context = VisualContext(messages)
        context.observe(png(size=(3000, 2000)))
        data = base64.b64decode(messages[-1]["images"][0])
        with Image.open(io.BytesIO(data)) as image:
            self.assertLessEqual(max(image.size), 1600)
        self.assertLessEqual(len(data), 2 * 1024**2)
        self.assertIn("omitted", context.observe(b"invalid"))
        self.assertFalse(any(message.get("images") for message in messages))


class CaptureTests(WorkspaceTest):
    def test_replaced_identity_is_preserved(self):
        captures = Captures(self.policy.state)
        path = Path(captures.write(png()))
        saved = path.with_suffix(".original")
        path.rename(saved)
        path.write_bytes(png("red"))
        try:
            with self.assertRaises(Denied):
                captures.close()
            self.assertEqual(path.read_bytes(), png("red"))
        finally:
            path.unlink()
            saved.rename(path)
            captures.close()

    def test_unknown_file_blocks_cleanup_without_recursive_deletion(self):
        captures = Captures(self.policy.state)
        path = captures.path / "unknown.png"
        path.write_bytes(png())
        with self.assertRaises(OSError):
            captures.close()
        self.assertEqual(Captures.recover(self.policy.state), [captures.run])
        self.assertTrue(path.exists())
        path.unlink()
        self.assertEqual(Captures.recover(self.policy.state), [])
        captures.close()

    def test_active_lease_survives_recovery_and_consume_removes_only_owned(self):
        captures = Captures(self.policy.state)
        self.addCleanup(captures.close)
        path = Path(captures.write(png()))
        attachment = self.policy.state / "attachment.png"
        attachment.write_bytes(png("red"))
        self.assertEqual(Captures.recover(self.policy.state), [])
        self.assertTrue(path.exists())
        with self.assertRaises(Denied):
            captures.consume(attachment)
        self.assertEqual(captures.consume(path), png())
        self.assertFalse(path.exists())
        self.assertEqual(attachment.read_bytes(), png("red"))

    def test_crashed_owner_recovery_preserves_unregistered_files(self):
        script = (
            "import os,sys; from local_agent.captures import Captures; "
            "c=Captures(sys.argv[1]); print(c.write(bytes.fromhex(sys.argv[2])),flush=True); os._exit(0)"
        )
        result = subprocess.run([sys.executable, "-c", script, str(self.policy.state), png().hex()],
                                capture_output=True, text=True, timeout=10, check=True)
        path = Path(result.stdout.strip())
        legacy = self.policy.state / "browser-unregistered.png"
        legacy.write_bytes(png("red"))
        self.assertTrue(path.exists())
        self.assertEqual(Captures.recover(self.policy.state), [])
        self.assertFalse(path.parent.exists())
        self.assertTrue(legacy.exists())

    def test_joined_worker_and_owner_cleanup(self):
        parent = Captures(self.policy.state)
        self.addCleanup(parent.close)
        worker = Captures(self.policy.state, parent.run)
        path = Path(worker.write(png()))
        worker.close()
        self.assertFalse(path.exists())
        self.assertTrue(parent.path.exists())
        parent.close()
        self.assertFalse(parent.path.exists())

    def test_hardlink_is_never_read_or_deleted(self):
        captures = Captures(self.policy.state)
        self.addCleanup(captures.close)
        path = Path(captures.write(png()))
        alias = self.policy.state / "alias.png"
        os.link(path, alias)
        try:
            with self.assertRaises(Denied):
                captures.consume(path)
            self.assertTrue(path.exists())
            self.assertTrue(alias.exists())
        finally:
            alias.unlink()


class CaptureLifecycleTests(StudioProcessFixture, WorkspaceTest):
    def test_cancel_removes_owned_capture_and_preserves_attachment_file(self):
        task = self.manager.start(self.conversation, "Write a reviewed file", "agent", "fixture")
        self.wait_until(lambda: bool(self.manager.pending()))
        captures = self.manager.running[task]["captures"]
        worker = Captures(self.policy.state, captures.run)
        path = Path(worker.write(png()))
        attachment = self.policy.state / "user-image.png"
        attachment.write_bytes(png("red"))
        self.manager.cancel(task)
        self.wait_until(lambda: not self.manager.running)
        self.assertFalse(path.parent.exists())
        self.assertTrue(attachment.exists())
        self.assertEqual(Captures.recover(self.policy.state), [])


@unittest.skipUnless(os.getenv("LIVE_IMAGE_CONTEXT") == "1", "Actual Ollama/browser image workflow is opt-in")
class LiveImageContextTests(WorkspaceTest):
    def test_studio_preview_cleanup_and_attachment_survival(self):
        self.config["browser"]["channel"] = os.getenv("LOCAL_AGENT_BROWSER_CHANNEL", "msedge")
        self.config["browser"]["headless"] = True
        with FixtureSite() as site:
            self.config["browser"]["allowed_origins"].append(site.url)
            manager = Manager(self.config)
            self.addCleanup(manager.close)
            conversation = manager.store.conversation()
            attachment = manager.store.attachment(conversation, parse_attachment("original.png", png("red")))
            original = manager.store.attachments(conversation, ids=[attachment["id"]], include_data=True)[0]["data"]
            manager.start(conversation, f"Open {site.url} with browser_open, then call browser_screenshot. "
                          "Only after taking the screenshot, report the solid color of my ORIGINAL attached image.",
                          "agent", self.config["model"]["name"], attachment_ids=[attachment["id"]])
            deadline = time.monotonic() + 120
            while manager.running and time.monotonic() < deadline:
                time.sleep(0.1)
            self.assertFalse(manager.running)
            self.assertIn("red", manager.store.messages(conversation)[-1]["content"].lower())
            previews = [event for event in manager.live_events if event["kind"] == "preview"]
            self.assertTrue(previews, manager.store.tasks())
            self.assertTrue(base64.b64decode(previews[0]["payload"]["image"]).startswith(b"\x89PNG"))
            self.assertEqual(manager.store.attachments(conversation, ids=[attachment["id"]],
                                                      include_data=True)[0]["data"], original)
            self.assertFalse(list((self.policy.state / "captures").glob("*/*.png")))

    def test_original_image_after_real_browser_screenshot(self):
        original = base64.b64encode(png("red")).decode()
        observed = []

        class RecordingOllama(Ollama):
            def chat(model, messages, **kwargs):
                if any("Untrusted transient visual observation" in message.get("content", "")
                       for message in messages):
                    observed.append([image for message in messages for image in message.get("images", [])])
                return super().chat(messages, **kwargs)

        self.config["browser"]["channel"] = os.getenv("LOCAL_AGENT_BROWSER_CHANNEL", "msedge")
        self.config["browser"]["headless"] = True
        with FixtureSite() as site:
            self.config["browser"]["allowed_origins"].append(site.url)
            tools = Tools(self.policy)
            self.addCleanup(tools.close)
            objective = (f"Open {site.url} using browser_open. Then call browser_screenshot. "
                         "After the screenshot, report the solid color of my ORIGINAL attached image "
                         "and describe how it differs from the browser screenshot. Do not write any files.")
            result = Agent(RecordingOllama(self.config["model"]), tools, self.config["model"]).run(
                objective, user_message={"role": "user", "content": objective, "images": [original]})
            self.assertEqual(result["status"], "reported", result)
            successful = {item["tool"] for item in result["evidence"] if item["ok"]}
            self.assertTrue({"browser_open", "browser_screenshot"} <= successful, result)
            self.assertTrue(observed, "No real model request after screenshot")
            self.assertTrue(all(len(images) == 2 and images[0] == original for images in observed))
            self.assertIn("red", result["report"].lower())
            self.assertFalse(list(tools.captures.path.glob("*.png")))
