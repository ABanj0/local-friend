import importlib.util
import json
import os
import socket
import subprocess
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from .runtime_command import runtime_command
from .support import WorkspaceTest


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("uvicorn", "fastapi")),
                     "Requires desktop dependencies")
class StudioRuntimeTests(WorkspaceTest):
    def launch_runtime(self, *, port=0, credential=True, missing_config=False):
        config = Path(self.temp.name) / "runtime.toml"
        if not missing_config:
            config.write_text(Path("agent.toml").read_text(), encoding="utf-8")
        env = dict(os.environ)
        env.pop("LOCAL_AGENT_STUDIO_TOKEN", None)
        if credential:
            env["LOCAL_AGENT_STUDIO_TOKEN"] = "runtime-launch-test-" * 3
        proc = subprocess.Popen([*runtime_command(), "--config",
                                 str(config), "--port", str(port)], env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def cleanup():
            if not proc.stdin.closed:
                proc.stdin.close()
            try:
                proc.wait(8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(5)
            proc.stdout.close()
            proc.stderr.close()

        self.addCleanup(cleanup)
        return proc

    def test_eof_stops_actual_backend_and_releases_listener(self):
        proc = self.launch_runtime()
        ready = json.loads(proc.stdout.readline())
        self.assertIn("port", ready)
        proc.stdin.close()
        self.assertEqual(proc.wait(8), 0)
        with socket.socket() as connection:
            self.assertNotEqual(connection.connect_ex(("127.0.0.1", ready["port"])), 0)

    def test_port_collision_reports_error_and_preserves_other_listener(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            proc = self.launch_runtime(port=listener.getsockname()[1])
            message = json.loads(proc.stdout.readline())
            self.assertIn("occupied", message["error"])
            self.assertEqual(proc.wait(5), 1)
            with socket.create_connection(listener.getsockname(), timeout=2):
                pass

    def test_missing_credential_and_configuration_are_explicit(self):
        for options, expected in [({"credential": False}, "credential"),
                                  ({"missing_config": True}, "configuration")]:
            with self.subTest(options=options):
                config = Path(self.temp.name) / "runtime.toml"
                config.unlink(missing_ok=True)
                proc = self.launch_runtime(**options)
                message = json.loads(proc.stdout.readline())
                self.assertIn(expected, message["error"])
                self.assertEqual(proc.wait(5), 1)

    def test_spawn_through_actual_runtime(self):
        class Fixture(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                from .ollama_fixture import serve_metadata
                if serve_metadata(self):
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"models":[{"name":"fixture"}]}')

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                from .ollama_fixture import serve_metadata
                if serve_metadata(self, body):
                    return
                if body.get("format"):
                    message = {"content": '{"steps":["List files"]}'}
                elif any(m["role"] == "tool" for m in body["messages"]):
                    message = {"content": "Files inspected"}
                else:
                    message = {"tool_calls": [{"function": {"name": "files", "arguments": {}}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"message": {"role": "assistant", **message}, "done": True, "done_reason": "stop"}).encode())

        server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        config = Path(self.temp.name) / "agent.toml"
        config.write_text(Path("agent.toml").read_text().replace("127.0.0.1:11434",
                          f"127.0.0.1:{server.server_port}"), encoding="utf-8")
        token = "runtime-test-credential-" * 3
        proc = subprocess.Popen([*runtime_command(),
                                 "--config", str(config), "--port", "0"],
                                env=dict(os.environ, LOCAL_AGENT_STUDIO_TOKEN=token),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)

        def cleanup():
            if proc.poll() is None:
                proc.stdin.write("shutdown\n")
                proc.stdin.flush()
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(5)
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()

        self.addCleanup(cleanup)
        ready = json.loads(proc.stdout.readline())
        self.assertIn("port", ready, ready)
        opener = build_opener(ProxyHandler({}))

        def call(path, body=None):
            request = Request(f"http://127.0.0.1:{ready['port']}{path}",
                              data=None if body is None else json.dumps(body).encode(),
                              headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
            with opener.open(request, timeout=5) as response:
                return json.load(response)

        for _ in range(30):
            try:
                call("/health")
                break
            except URLError:
                time.sleep(0.1)
        conversation = call("/conversations", {})["id"]
        call("/tasks", {"conversation": conversation, "model": "fixture",
                        "mode": "agent", "objective": "List the workspace files using files and report the result."})
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            task = call("/tasks")["tasks"][0]
            if task["status"] != "running":
                self.assertEqual(task["status"], "reported", task)
                proc.stdin.write("shutdown\n")
                proc.stdin.flush()
                self.assertEqual(proc.wait(5), 0, "Backend did not shut down cleanly")
                return
            time.sleep(0.2)
        self.fail("Task never finished through runtime subprocess")
