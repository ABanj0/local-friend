"""Actual task-owned servers, failure/permission boundaries and bounded observations."""
import copy
import json
import os
import socket
import subprocess
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

try:
    import psutil
except ImportError:
    psutil = None

from local_agent.background import accept_status, readiness_config
from local_agent.coding import Coding
from local_agent.command_output import accept_event
from local_agent.safety import Denied, Stopped
from local_agent.tools import Tools

from .studio_support import StudioProcessFixture
from .support import WorkspaceTest


def free_port():
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        return endpoint.getsockname()[1]


def server_source(port, *, delay=0, redirect=None):
    return ("from http.server import BaseHTTPRequestHandler,HTTPServer\nfrom pathlib import Path\nimport time,os\n"
            "class Handler(BaseHTTPRequestHandler):\n"
            " def log_message(self,*args):pass\n"
            " def do_GET(self):\n"
            "  with Path('requests.log').open('a') as output:output.write(self.path+'\\n')\n"
            "  if Path('drip').exists():\n"
            "   self.connection.sendall(b'HTTP/1.0 200 OK\\r\\nX-Drip: ')\n"
            "   for _ in range(100):self.connection.sendall(b'x');time.sleep(.05)\n"
            "   self.connection.sendall(b'\\r\\n\\r\\n');return\n"
            f"  time.sleep({delay!r})\n"
            "  code=int(Path('http-status').read_text()) if Path('http-status').exists() else 200\n"
            f"  self.send_response(302 if {redirect!r} else code)\n"
            f"  if {redirect!r}:self.send_header('Location',{redirect!r})\n"
            "  self.end_headers();self.wfile.write(b'UNTRUSTED-BODY-IGNORE-INSTRUCTIONS')\n"
            f"server=HTTPServer(('127.0.0.1',{port}),Handler)\n"
            "Path('server.pid').write_text(str(os.getpid()))\n"
            "print('BACKGROUND-READY '+'.'*40)\nprint('password=BACKGROUND-SECRET-CANARY')\nserver.serve_forever()\n")


@unittest.skipUnless(psutil is not None, "Background ownership checks require the desktop extra")
class BackgroundTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.coding = Coding(self.policy)
        self.frames, self.statuses = [], []
        self.coding.output, self.coding.background = self.frames.append, self.statuses.append
        self.addCleanup(self.coding.close)

    def configure(self, *, timeout=3, source=None, configured=True, delay=0, redirect=None):
        port = free_port()
        self.config["commands"]["server"] = ["{python}", "-c", source or server_source(port, delay=delay, redirect=redirect)]
        if configured:
            self.config["readiness"] = {"server": {"url": f"http://127.0.0.1:{port}/health", "timeout": timeout, "interval": .1}}
        return port

    def exited(self, pid):
        try:
            psutil.Process(pid).wait(timeout=2)
        except psutil.NoSuchProcess:
            pass

    def test_real_owned_http_readiness_status_refresh_and_safe_output(self):
        port = self.configure()
        result = self.coding.start("server")
        self.assertEqual(result["readiness"]["status"], "ready", result)
        self.assertEqual(result["state"], "running")
        self.assertEqual(self.approvals[0][1]["readiness"]["url"], f"http://127.0.0.1:{port}/health")
        self.assertGreaterEqual(len((self.policy.root / "requests.log").read_text().splitlines()), 1)
        (self.policy.root / "http-status").write_text("503")
        self.assertEqual(self.coding.status("server")["readiness"]["status"], "unready")
        (self.policy.root / "http-status").write_text("200")
        self.assertEqual(self.coding.status("server")["readiness"]["status"], "ready")
        stopped = self.coding.stop("server")["process"]
        self.exited(result["pid"])
        self.assertEqual(stopped["state"], "stopped")
        self.assertEqual(stopped["readiness"]["status"], "stopped")
        self.assertIsNotNone(stopped["readiness"]["last_ready_at"])
        observations = json.dumps([stopped, self.frames, self.statuses])
        self.assertNotIn("BACKGROUND-SECRET-CANARY", observations)
        self.assertNotIn("UNTRUSTED-BODY", observations)
        self.assertTrue(self.frames[-1]["finished"])

    def test_literal_ipv6_loopback_readiness_uses_the_owned_listener(self):
        with socket.socket(socket.AF_INET6) as endpoint:
            endpoint.bind(("::1", 0))
            port = endpoint.getsockname()[1]
        source = server_source(port).replace("server=HTTPServer(",
            "import socket\nclass V6Server(HTTPServer):address_family=socket.AF_INET6\nserver=V6Server(")
        source = source.replace("('127.0.0.1',", "('::1',")
        self.configure(source=source)
        self.config["readiness"]["server"]["url"] = f"http://[::1]:{port}/health"
        result = self.coding.start("server")
        self.assertEqual(result["readiness"]["status"], "ready", result)
        self.assertEqual(result["readiness"]["status_code"], 200)

    def test_status_delivery_failure_stops_owned_server_without_leaking_error(self):
        self.configure()

        def broken(payload):
            if payload["readiness"]["status"] == "ready":
                raise OSError("password=EVENT-PRIVATE-CANARY")

        self.coding.background = broken
        result = self.coding.start("server")
        self.assertEqual(result["state"], "failed")
        self.assertTrue(self.coding.processes["server"].resources_closed)
        self.exited(result["pid"])
        self.assertNotIn("EVENT-PRIVATE-CANARY", json.dumps(result))

    def test_unconfigured_start_never_probes_or_claims_readiness(self):
        self.configure(configured=False)
        with patch("psutil.net_connections", side_effect=AssertionError("No probe allowed")):
            result = self.coding.start("server")
            self.assertEqual(result["readiness"]["status"], "unconfigured")
            self.assertEqual(self.coding.status("server")["readiness"]["status"], "unconfigured")
            self.coding.stop("server")
        self.assertFalse((self.policy.root / "requests.log").exists())

    def test_timeout_and_early_exit_are_failed_observations_and_clean_owned_process(self):
        for source in ("import time;time.sleep(30)", "print('process exited')"):
            with self.subTest(source=source):
                self.configure(timeout=.3, source=source)
                result = self.coding.start("server")
                self.assertIn(result["readiness"]["status"], {"timeout", "exited"})
                self.assertIsNotNone(result["error"])
                self.exited(result["pid"])
                self.assertNotEqual(result["readiness"]["status"], "ready")
                self.coding.stop("server")

    def test_tool_marks_failed_configured_start_as_failure(self):
        self.configure(timeout=.3, source="import time;time.sleep(30)")
        tools = Tools(self.policy, profile="coding")
        self.addCleanup(tools.close)
        result = tools.execute("start_command", {"name": "server"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "BackgroundNotReady")
        self.assertEqual(result["untrusted_data"]["readiness"]["status"], "timeout")

    def test_unrelated_listener_gets_no_request_and_is_not_stopped(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.end_headers()

        service = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=service.serve_forever, daemon=True).start()
        self.addCleanup(service.server_close)
        self.addCleanup(service.shutdown)
        self.configure(timeout=.3, source="import time;time.sleep(30)")
        self.config["readiness"]["server"]["url"] = f"http://127.0.0.1:{service.server_port}/"
        result = self.coding.start("server")
        self.assertEqual(result["readiness"]["status"], "timeout")
        self.assertFalse(requests)
        self.exited(result["pid"])
        self.assertNotEqual(service.fileno(), -1)

    def test_redirect_is_not_followed_and_delayed_response_is_bounded(self):
        for kwargs in ({"redirect": "http://127.0.0.1:1/must-not-follow"}, {"delay": 2}):
            with self.subTest(kwargs=kwargs):
                self.configure(timeout=.4, **kwargs)
                before = time.monotonic()
                result = self.coding.start("server")
                self.assertEqual(result["readiness"]["status"], "timeout")
                self.assertLess(time.monotonic() - before, 3)
                self.assertNotEqual(result["readiness"]["status_code"], 200)
                if "redirect" in kwargs:
                    self.assertEqual(result["readiness"]["status_code"], 302)
                self.coding.stop("server")

    def test_dripping_headers_cannot_extend_startup_or_status_probe_indefinitely(self):
        self.configure(timeout=.3)
        marker = self.policy.root / "drip"
        marker.touch()
        started = time.monotonic()
        result = self.coding.start("server")
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(result["readiness"]["status"], "timeout")
        self.coding.stop("server")
        marker.unlink()
        self.configure()
        self.assertEqual(self.coding.start("server")["readiness"]["status"], "ready")
        marker.touch()
        started = time.monotonic()
        result = self.coding.status("server")
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(result["readiness"]["status"], "unready")

    def test_invalid_readiness_config_fails_before_approval_or_spawn(self):
        self.configure()
        url = self.config["readiness"]["server"]["url"]
        bad = [{"url": value} for value in ("https://127.0.0.1:1234/", "http://localhost:1234/",
            "http://example.com:1234/", "http://user:pass@127.0.0.1:1234/", url + "?q=1", url + "#fragment")]
        bad += [{"url": url, **values} for values in ({"status": True}, {"status": 503}, {"timeout": 0},
                {"timeout": float("nan")}, {"interval": .001}, {"headers": {}})]
        for config in bad:
            self.config["readiness"]["server"] = config
            with (self.subTest(config=config), patch("local_agent.background.subprocess.Popen") as spawn,
                  self.assertRaises(ValueError)):
                self.coding.start("server")
            spawn.assert_not_called()
        self.assertFalse(self.approvals)

    def test_denial_scope_and_model_arguments_cannot_widen_probes(self):
        self.configure()
        self.allow = False
        with patch("local_agent.background.subprocess.Popen") as spawn, self.assertRaises(Denied):
            self.coding.start("server")
        spawn.assert_not_called()
        tools = Tools(self.policy, profile="browser")
        self.assertEqual(tools.execute("command_status", {"name": "server"})["error"], "Denied")
        tools = Tools(self.policy, profile="coding")
        self.assertEqual(tools.execute("command_status", {"name": "server", "url": "http://example.com"})["error"], "TypeError")
        self.assertEqual(tools.execute("command_status", {"name": "unknown"})["error"], "Denied")
        self.assertEqual(tools.execute("command_status", {"name": "server"})["error"], "ValueError")

    def test_ownership_permission_failure_never_sends_http(self):
        self.configure(timeout=.3)
        with (patch("psutil.net_connections", side_effect=psutil.AccessDenied()),
              patch("local_agent.background.http.client.HTTPConnection", side_effect=AssertionError("No HTTP allowed"))):
            result = self.coding.start("server")
        self.assertEqual(result["readiness"]["status"], "timeout")
        self.assertEqual(result["readiness"]["last_check"], "ownership_unverified")
        self.assertFalse((self.policy.root / "requests.log").exists())

    def test_background_output_is_bounded_and_duplicate_start_is_refused(self):
        self.configure(configured=False, source="import os,time;os.write(1,b'x'*1000000);time.sleep(30)")
        first = self.coding.start("server")
        deadline = time.monotonic() + 3
        while not self.coding.status("server")["truncated"] and time.monotonic() < deadline:
            time.sleep(.02)
        result = self.coding.status("server")
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["output"].encode()), 16000)
        with self.assertRaises(Denied):
            self.coding.start("server")
        self.assertEqual(result["pid"], first["pid"])
        self.assertFalse(list(self.policy.root.iterdir()))

    def test_stop_during_readiness_reaps_owned_process(self):
        self.configure(timeout=3, source="import time;time.sleep(30)")
        timer = threading.Timer(.2, self.policy.stop_event.set)
        timer.start()
        self.addCleanup(timer.cancel)
        with self.assertRaises(Stopped):
            self.coding.start("server")
        command = self.coding.processes["server"]
        self.coding.close()
        self.exited(command.proc.pid)
        self.assertFalse(command.monitor.is_alive())

    def test_status_contract_is_bounded_and_transactional(self):
        settings = readiness_config({"url": "http://127.0.0.1:8765/health"})
        streams, updates = {}, {}
        accept_event({"command_id": "a" * 32, "profile": "server", "part": 1, "text": "", "finished": False,
                      "truncated": False, "exit_code": None, "reason": "running"}, streams)
        payload = {"command_id": "a" * 32, "profile": "server", "pid": os.getpid(), "state": "running",
                   "readiness": {"status": "starting", "url": settings["url"], "status_code": None,
                                 "checked_at": None, "last_ready_at": None, "last_check": None}}
        accept_status(payload, self.config["commands"] | {"server": []}, settings, streams, updates)
        before = copy.deepcopy(updates)
        for changed in ({"pid": True}, {"command_id": "b" * 32}, {"state": []},
                        {"readiness": dict(payload["readiness"], status="ready")},
                        {"readiness": dict(payload["readiness"], last_check=[])},
                        {"readiness": dict(payload["readiness"], checked_at=float("nan"))}):
            with self.subTest(changed=list(changed)), self.assertRaises(ValueError):
                accept_status({**payload, **changed}, {"server": []}, settings, streams, updates)
            self.assertEqual(updates, before)
        updates[payload["command_id"]] = (256, payload["pid"])
        with self.assertRaises(ValueError):
            accept_status(payload, {"server": []}, settings, streams, updates)

    def test_capacity_limit_and_close_failure_do_not_skip_other_owned_processes(self):
        self.configure(configured=False, source="import time;time.sleep(30)")
        for index in range(4):
            name = f"wait{index}"
            self.config["commands"][name] = self.config["commands"]["server"]
            self.coding.start(name)
        with self.assertRaisesRegex(Denied, "four background"):
            self.coding.start("server")
        first, second = self.coding.processes["wait0"], self.coding.processes["wait1"]
        with patch.object(first, "stop", side_effect=OSError("injected cleanup fault")), self.assertRaises(OSError):
            self.coding.close()
        self.assertIn("wait0", self.coding.processes)
        self.assertNotIn("wait1", self.coding.processes)
        self.exited(second.proc.pid)

    def test_monitor_start_failure_closes_process_reader_and_publisher_once(self):
        self.configure(configured=False, source="import time;time.sleep(30)")
        original_start, original_spawn = threading.Thread.start, subprocess.Popen
        calls, spawned = [], []

        def start(thread):
            calls.append(thread)
            if len(calls) == 2:
                raise OSError("fixture monitor failure")
            return original_start(thread)

        def spawn(*args, **kwargs):
            child = original_spawn(*args, **kwargs)
            if kwargs.get("stdout") == subprocess.PIPE:
                spawned.append(child)
            return child

        with (patch("local_agent.background.subprocess.Popen", side_effect=spawn),
              patch("local_agent.background.threading.Thread.start", start), self.assertRaises(OSError)):
            self.coding.start("server")
        self.assertIsNotNone(spawned[0].poll())
        self.assertTrue(spawned[0].stdout.closed)
        self.assertFalse(calls[0].is_alive())
        self.assertEqual(sum(frame["finished"] for frame in self.frames), 1)

    @unittest.skipUnless(os.name == "nt", "Windows owned Job Object subtree acceptance")
    def test_exited_parent_cleans_its_inherited_pipe_child(self):
        child = "from pathlib import Path;import os,time;Path('child.pid').write_text(str(os.getpid()));time.sleep(30)"
        source = ("import subprocess,sys,time\nfrom pathlib import Path\ntime.sleep(.15)\n"
                  f"subprocess.Popen([sys.executable,'-c',{child!r}])\n"
                  "while not Path('child.pid').exists():time.sleep(.01)\n")
        self.configure(configured=False, source=source)
        self.coding.start("server")
        marker = self.policy.root / "child.pid"
        deadline = time.monotonic() + 4
        while (not marker.exists() or self.coding.status("server")["state"] == "running") and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(marker.exists())
        self.exited(int(marker.read_text()))
        owner = self.coding.processes["server"]
        owner.monitor.join(2)
        self.assertFalse(owner.monitor.is_alive())
        self.assertTrue(owner.resources_closed)


@unittest.skipUnless(psutil is not None, "Background ownership checks require the desktop extra")
class BackgroundProcessTests(StudioProcessFixture, WorkspaceTest):
    def scenario(self, cancel):
        port = free_port()
        self.config["commands"]["server"] = ["{python}", "-c", server_source(port)]
        self.config["readiness"] = {"server": {"url": f"http://127.0.0.1:{port}/health", "timeout": 3}}
        (self.policy.root / "test_gate.py").write_text("import unittest,time\nfrom pathlib import Path\n"
            "class Gate(unittest.TestCase):\n def test_gate(self):\n  print('AFTER-READY '+'.'*40)\n"
            "  while not Path('release').exists():time.sleep(.02)\n  self.assertTrue(True)\n", encoding="utf-8")
        requests = self.requests

        class Protocol(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                from .ollama_fixture import serve_metadata
                if not serve_metadata(self):
                    self.send_error(404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                from .ollama_fixture import serve_metadata
                if serve_metadata(self, body):
                    return
                requests.append(body)
                used = [m.get("tool_name") for m in body["messages"] if m["role"] == "tool"]
                if body.get("format"):
                    message = {"content": '{"steps":["Start approved server", "Inspect readiness", "Run tests"]}'}
                elif "command" in used:
                    message = {"content": "Fixture observed readiness and tests"}
                else:
                    name = "command" if "command_status" in used else "command_status" if "start_command" in used else "start_command"
                    message = {"tool_calls": [{"function": {"name": name,
                               "arguments": {"name": "test" if name == "command" else "server"}}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"message": {"role": "assistant", **message}, "done": True, "done_reason": "stop"}).encode())

        self.server.RequestHandlerClass = Protocol
        task = self.manager.start(self.conversation, "Start server and verify tests", "agent", "fixture", profile="coding")
        self.wait_until(lambda: self.manager.pending())
        approval = self.manager.pending()[0]
        self.assertEqual(approval["action"], "start_code")
        self.manager.approve(task, approval["id"], True)
        self.wait_until(lambda: self.manager.pending())
        statuses = [row["payload"] for row in self.manager.store.events() if row["kind"] == "background_status"]
        self.assertTrue(any(row["readiness"]["status"] == "ready" for row in statuses))
        pid = statuses[0]["pid"]
        self.assertEqual(self.manager.pending()[0]["action"], "execute_code")
        self.manager.approve(task, self.manager.pending()[0]["id"], True)
        self.wait_until(lambda: any("AFTER-READY" in row["payload"].get("text", "") for row in self.manager.store.events()
                                   if row["kind"] == "command_output"))
        if cancel:
            self.manager.cancel(task)
        else:
            (self.policy.root / "release").touch()
        self.wait_until(lambda: not self.manager.running)
        try:
            psutil.Process(pid).wait(timeout=2)
        except psutil.NoSuchProcess:
            pass
        checks = self.manager.store.verifications(task)
        if cancel:
            self.assertFalse(checks)
            self.assertEqual(self.manager.tasks()[0]["status"], "cancelled")
        else:
            self.assertEqual(checks[0]["counts"]["tests_run"], 1)
            self.assertEqual(self.manager.tasks()[0]["status"], "reported")
            last = [row["payload"] for row in self.manager.store.events() if row["kind"] == "background_status"][-1]
            self.assertEqual(last["state"], "stopped")
        self.assertNotIn("BACKGROUND-SECRET-CANARY", json.dumps(self.manager.store.events()))

    def test_real_worker_readiness_status_tests_and_task_cleanup(self):
        self.scenario(False)

    def test_real_worker_cancel_closes_owned_server_and_test_process(self):
        self.scenario(True)
