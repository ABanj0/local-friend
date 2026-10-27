"""Reusable Studio fixtures; mixins deliberately do not inherit unittest.TestCase."""
import importlib.util
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from local_agent.studio.manager import Manager

from .ollama_fixture import serve_metadata

HAS_API = all(importlib.util.find_spec(name) for name in ("fastapi", "httpx"))


class StudioProcessFixture:
    """Protocol fixture with real worker processes, approvals and filesystem tools."""
    def setUp(self):
        super().setUp()

        self.requests = []
        requests = self.requests
        stream_chunks = getattr(self, "stream_chunks", ("hello ", "world"))
        stream_final_gate = getattr(self, "stream_final_gate", None)
        finish_reason = getattr(self, "finish_reason", "stop")

        class ProtocolFixture(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if not serve_metadata(self):
                    self.send_error(404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if serve_metadata(self, body):
                    return
                requests.append(body)
                reason = finish_reason(body) if callable(finish_reason) else finish_reason
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if body.get("stream"):
                    for text in stream_chunks:
                        self.wfile.write(json.dumps({"message": {"content": text}}).encode() + b"\n")
                    if stream_final_gate is not None:
                        stream_final_gate.wait(5)
                    try:
                        self.wfile.write(json.dumps({"done": True, "done_reason": reason,
                            "eval_count": 80, "eval_duration": 2_000_000_000}).encode() + b"\n")
                    except ConnectionError:
                        pass  # Cancellation intentionally closes a gated fixture response.
                    return
                if body.get("format"):
                    message = {"content": json.dumps({"steps": ["Write the reviewed fixture file"]})}
                elif any(m["role"] == "tool" for m in body["messages"]):
                    message = {"content": "Action completed"}
                else:
                    message = {"content": "", "tool_calls": [{"function": {
                        "name": "write_file", "arguments": {"path": "review.txt", "text": "reviewed"}}}]}
                message["role"] = "assistant"
                self.wfile.write(json.dumps({"message": message, "done": True, "done_reason": reason,
                                            "eval_count": 10, "eval_duration": 500000000}).encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ProtocolFixture)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.config["model"]["url"] = f"http://127.0.0.1:{self.server.server_port}"
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.conversation = self.manager.store.conversation()

    def wait_until(self, condition):
        deadline = time.monotonic() + 15
        while not condition() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(condition(), "Worker/approval did not settle")


class StudioAPIFixture:
    """Authenticated TestClient setup shared without inheriting concrete API tests."""
    def setUp(self):
        super().setUp()
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from local_agent.inference import CapabilityCache
        from local_agent.studio.api import create_app
        self.enterContext(patch("local_agent.model.CAPABILITIES", CapabilityCache()))
        self.client = TestClient(create_app(self.config, "x" * 64))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.headers = {"Authorization": "Bearer " + "x" * 64}
