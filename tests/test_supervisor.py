import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from local_agent.cli import supervise

from .ollama_fixture import serve_metadata
from .support import WorkspaceTest


class SupervisorTests(WorkspaceTest):
    def test_stop_interrupts_blocked_model_request(self):
        entered = threading.Event()
        release = threading.Event()
        model_name = self.config["model"]["name"]

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                import json
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if serve_metadata(self, body, name=model_name):
                    return
                entered.set()
                release.wait(10)

            def do_GET(self):
                if not serve_metadata(self, name=model_name):
                    self.send_error(404)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(release.set)
        source = Path("agent.toml").read_text()
        source = source.replace('workspace = "workspace"', 'workspace = "work"')
        source = source.replace('state = ".runtime/state"', 'state = "state"')
        source = source.replace("127.0.0.1:11434", f"127.0.0.1:{server.server_port}")
        config_path = Path(self.temp.name) / "agent.toml"
        config_path.write_text(source)

        def stop_after_request():
            entered.wait(5)
            (self.policy.state / "STOP").touch()

        stopper = threading.Thread(target=stop_after_request, daemon=True)
        stopper.start()
        started = time.monotonic()
        status = supervise(config_path, self.config, "Test cancellation; perform no actions")
        stopper.join(timeout=1)
        self.assertTrue(entered.is_set(), "Worker never reached local model protocol fixture")
        self.assertEqual(status, 130)
        self.assertLess(time.monotonic() - started, 5)
