import io
import os
import time
import unittest
from unittest.mock import patch

try:
    from PIL import Image
except ImportError:
    Image = None

from local_agent.studio.attachments import MAX_UPLOAD, model_message, parse_attachment
from local_agent.studio.manager import Manager
from local_agent.studio.store import Store

from . import studio_support as fixtures
from .support import WorkspaceTest


@unittest.skipUnless(Image, "Pillow is required for attachment image tests")
class AttachmentStoreTests(WorkspaceTest):
    def test_images_text_and_invalid_payloads(self):
        image = Image.new("RGB", (2000, 1000), "red")
        output = io.BytesIO()
        image.save(output, format="PNG")
        attachment = parse_attachment("screen.png", output.getvalue())
        normalized = Image.open(io.BytesIO(attachment["data"]))
        self.assertEqual(normalized.size, (1600, 800))
        self.assertEqual(attachment["mime"], "image/jpeg")
        self.assertEqual(parse_attachment("code.py", b"print(42)")["text"], "print(42)")
        for name, data in [("../x.txt", b"x"), ("C:\\secret.txt", b"x"), (".env", b"x"),
                           ("key.pem", b"x"), ("screen.png", b"not an image"),
                           ("x.txt", b"\xff"), ("x.pdf", b"%PDF"), ("x.txt", b"x" * (MAX_UPLOAD+1))]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse_attachment(name, data)

    def test_message_binding_isolation_and_cascade_deletion(self):
        store = Store(self.policy.state / "features.db")
        first, other = store.conversation(), store.conversation()
        attachment = store.attachment(first, parse_attachment("readme.md", b"untrusted input"))
        with self.assertRaises(ValueError):
            store.attachments(other, ids=[attachment["id"]])
        message = store.message(first, "user", "Review this", attachment_ids=[attachment["id"]])
        self.assertEqual(store.messages(first)[0]["attachments"][0]["id"], attachment["id"])
        self.assertEqual(store.attachments(first, pending=True), [])
        with self.assertRaises(ValueError):
            store.message(first, "user", "reuse", attachment_ids=[attachment["id"]])
        self.assertEqual(len(store.messages(first)), 1)  # Failed binding rolled back the message.
        payload = model_message("Review this", store.attachments(first, message=message, include_data=True))
        self.assertIn("BEGIN UNTRUSTED ATTACHMENT", payload["content"])
        task = store.task(first, "chat", "fixture")
        store.event(task, "progress", {"text": "testing"})
        store.finish(task, "reported", {})
        store.rename_conversation(first, "Renamed")
        self.assertIn("Renamed", {row["title"] for row in store.conversations()})
        store.delete_conversation(first)
        self.assertEqual(store.tasks(), [])
        self.assertEqual(store.events(), [])
        self.assertEqual(store.attachments(first), [])
        self.assertEqual(store.messages(other), [])


@unittest.skipUnless(Image, "Pillow is required for attachment image tests")
@unittest.skipUnless(fixtures.HAS_API, "Desktop API dependencies not installed")
class FeatureAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_image_upload_requires_a_vision_model_and_upload_size_is_bounded(self):
        manager = self.client.app.state.manager
        conversation = manager.store.conversation()
        output = io.BytesIO()
        Image.new("RGB", (16,16), "red").save(output, format="PNG")
        image = manager.store.attachment(conversation, parse_attachment("red.png", output.getvalue()))
        from .ollama_fixture import metadata_response

        def text_only(endpoint, payload=None):
            response = metadata_response(endpoint, payload, name="text-only")
            if endpoint == "/api/show":
                response["capabilities"] = ["completion"]
            return response

        with patch("local_agent.studio.api.Ollama.request", side_effect=text_only):
            response = self.client.post("/tasks", json={"conversation":conversation, "model":"text-only",
                                                       "objective":"Inspect image", "attachments":[image["id"]]}, headers=self.headers)
            self.assertEqual(response.status_code, 400)
            self.assertIn("vision", response.json()["detail"])
        self.assertEqual(manager.store.tasks(), [])
        response = self.client.post(f"/conversations/{conversation}/attachments?name=big.txt",
                                    content=b"x"*(MAX_UPLOAD+1), headers=self.headers)
        self.assertEqual(response.status_code, 413)

    def test_upload_preview_confirmation_and_delete(self):
        ident = self.client.post("/conversations", json={}, headers=self.headers).json()["id"]
        url = f"/conversations/{ident}"
        self.assertEqual(self.client.post(url+"/attachments?name=x.txt", content=b"x").status_code, 401)
        attachment = self.client.post(url+"/attachments?name=hello.py", content=b"print(42)", headers=self.headers).json()
        response = self.client.get(url+f"/attachments/{attachment['id']}", headers=self.headers)
        self.assertEqual(response.json()["text"], "print(42)")
        self.assertEqual(self.client.post(url+"/screenshot", json={"confirmed":False}, headers=self.headers).status_code, 400)
        with patch("PIL.ImageGrab.grab", return_value=Image.new("RGB", (50,50), "red")) as capture:
            screenshot = self.client.post(url+"/screenshot", json={"confirmed":True}, headers=self.headers)
            self.assertEqual(screenshot.status_code, 200)
            self.assertTrue(screenshot.json()["mime"].startswith("image/"))
            capture.assert_called_once()
        self.assertEqual(self.client.post(url+"/delete", json={"confirmed":False}, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post(url+"/delete", json={"confirmed":True}, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get(url+"/messages", headers=self.headers).status_code, 404)

    def test_active_chat_deletion_and_foreign_attachment_are_rejected(self):
        manager = self.client.app.state.manager
        first, other = manager.store.conversation(), manager.store.conversation()
        attachment = manager.store.attachment(first, parse_attachment("x.txt", b"x"))
        self.assertEqual(self.client.get(f"/conversations/{other}/attachments/{attachment['id']}", headers=self.headers).status_code, 400)
        manager.running["fixture"] = {"conversation":first}
        try:
            response = self.client.post(f"/conversations/{first}/delete", json={"confirmed":True}, headers=self.headers)
            self.assertEqual(response.status_code, 400)
        finally:
            manager.running.clear()
        self.assertEqual(self.client.get(f"/conversations/{first}/messages", headers=self.headers).status_code, 200)


@unittest.skipUnless(Image, "Pillow is required for attachment image tests")
class AttachmentProcessTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def test_attachment_reaches_real_worker_and_regeneration(self):
        attachment = self.manager.store.attachment(self.conversation, parse_attachment("context.md", b"MARKER-ATTACHED"))
        self.manager.start(self.conversation, "Read this", "chat", "fixture", attachment_ids=[attachment["id"]])
        self.wait_until(lambda: not self.manager.running)
        self.assertIn("MARKER-ATTACHED", self.requests[-1]["messages"][-1]["content"])
        self.assertEqual(self.manager.store.messages(self.conversation)[0]["attachments"][0]["id"], attachment["id"])
        self.manager.start(self.conversation, "", "chat", "fixture", regenerate=True)
        self.wait_until(lambda: not self.manager.running)
        self.assertEqual(len(self.manager.store.messages(self.conversation)), 3)
        self.assertIn("MARKER-ATTACHED", self.requests[-1]["messages"][-1]["content"])

    def test_image_is_passed_to_model_and_kept_in_history(self):
        output = io.BytesIO()
        Image.new("RGB", (32,32), "red").save(output, format="PNG")
        image = self.manager.store.attachment(self.conversation, parse_attachment("red.png", output.getvalue()))
        self.manager.start(self.conversation, "Inspect image", "chat", "fixture", attachment_ids=[image["id"]])
        self.wait_until(lambda: not self.manager.running)
        self.assertTrue(self.requests[-1]["messages"][-1]["images"])
        self.manager.start(self.conversation, "Remember the image", "chat", "fixture")
        self.wait_until(lambda: not self.manager.running)
        self.assertTrue(self.requests[-1]["messages"][1]["images"])


@unittest.skipUnless(os.getenv("LIVE_STUDIO_FEATURES") == "1", "Set LIVE_STUDIO_FEATURES=1 for actual model attachment tests")
@unittest.skipUnless(Image, "Pillow is required for attachment image tests")
class AttachmentLiveTests(WorkspaceTest):
    def test_model_reads_image_and_text_attachments(self):
        manager = Manager(self.config)
        self.addCleanup(manager.close)
        conversation = manager.store.conversation()
        output = io.BytesIO()
        Image.new("RGB", (64,64), "red").save(output, format="PNG")
        image = manager.store.attachment(conversation, parse_attachment("red.png", output.getvalue()))
        manager.start(conversation, "What is the predominant color of the attached image? Answer one color word.",
                      "chat", self.config["model"]["name"], attachment_ids=[image["id"]])

        def wait():
            deadline = time.monotonic()+120
            while manager.running and time.monotonic()<deadline:
                time.sleep(0.1)
            self.assertFalse(manager.running)

        wait()
        self.assertIn("red", manager.store.messages(conversation)[-1]["content"].lower())
        text = manager.store.attachment(conversation, parse_attachment("note.txt", b"The marker is ORCHID-FILE-812."))
        manager.start(conversation, "Return only the exact marker in the attached note.", "chat",
                      self.config["model"]["name"], attachment_ids=[text["id"]])
        wait()
        self.assertIn("ORCHID-FILE-812", manager.store.messages(conversation)[-1]["content"])


if __name__ == "__main__":
    unittest.main()
