"""Real loopback WebSocket authentication checks; no model or desktop required."""
import importlib.util
import json
import os
import queue
import secrets
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from local_agent.studio.store import Store

from .runtime_command import runtime_command

HAS_SOCKET = all(importlib.util.find_spec(name) for name in ("fastapi", "uvicorn", "websockets"))


class StudioSocketFixture:
    def setUp(self):
        super().setUp()
        config = Path(self.temp.name) / "agent.toml"
        config.write_text(Path("agent.toml").read_text(encoding="utf-8")
                          .replace('workspace = "workspace"', 'workspace = "work"')
                          .replace('state = ".runtime/state"', 'state = "state"'), encoding="utf-8")
        self.socket_config = config
        self.errors = self.enterContext(tempfile.TemporaryFile())
        self.addCleanup(self.stop_backend)
        self.start_backend()
        # Ensure a leaked snapshot contains observable private task data.
        self.store = Store(self.policy.state / "studio.sqlite3")
        conversation = self.store.conversation("WEBSOCKET-PRIVATE-CANARY")
        self.task = self.store.task(conversation, "chat", "PRIVATE-MODEL-CANARY")
        self.store.finish(self.task, "reported", {"report": "Private fixture result"})

    def start_backend(self):
        config = self.socket_config
        self.token = secrets.token_hex(32)
        self.proc = subprocess.Popen(
            [*runtime_command(), "--config", str(config), "--port", "0"],
            env=dict(os.environ, LOCAL_AGENT_STUDIO_TOKEN=self.token),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors, text=True)
        ready = queue.Queue()
        reader = threading.Thread(target=lambda: ready.put(self.proc.stdout.readline()), daemon=True)
        reader.start()
        info = json.loads(ready.get(timeout=10))
        reader.join(1)
        self.assertIn("port", info, info)
        self.port = info["port"]
        self.opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 5
        while True:
            try:
                self.http("/health")
                break
            except URLError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)

    def stop_backend(self):
        if not self.proc.stdin.closed and self.proc.poll() is None:
            self.proc.stdin.write("shutdown\n")
            self.proc.stdin.flush()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(5)
        self.proc.stdin.close()
        self.proc.stdout.close()
        self.errors.seek(0)
        errors = self.errors.read().decode("utf-8", "replace")
        self.assertNotIn(self.token, errors)
        self.assertNotIn("WRONG-AUTH-CANARY", errors)
        self.assertNotIn("Traceback", errors)

    def http(self, path):
        request = Request(f"http://127.0.0.1:{self.port}{path}",
                          headers={"Authorization": "Bearer " + self.token})
        with self.opener.open(request, timeout=3) as response:
            return json.load(response)

    def connect(self, origin="http://tauri.localhost"):
        from websockets.sync.client import connect
        return connect(f"ws://127.0.0.1:{self.port}/events", origin=origin, proxy=None,
                       open_timeout=3, close_timeout=1)

    def reject(self, frame):
        from websockets.exceptions import ConnectionClosedError
        with self.connect() as socket:
            socket.send(frame)
            with self.assertRaises(ConnectionClosedError) as closed:
                socket.recv(timeout=3)
            self.assertIsNotNone(closed.exception.rcvd)
            self.assertEqual(closed.exception.rcvd.code, 1008)
        self.assertTrue(self.http("/health")["ready"])
