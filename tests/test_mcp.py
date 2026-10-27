import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from local_agent.mcp_contract import MCPError, MCPReviewRequired, approved_path, read_text, settings
from local_agent.mcp_provider import ProjectProvider, require_sdk, server_command
from local_agent.safety import Denied, Stopped
from local_agent.tools import Tools

from .studio_support import StudioProcessFixture
from .support import WorkspaceTest

HAS_MCP = importlib.util.find_spec("mcp") is not None


class MCPPolicyTests(WorkspaceTest):
    def test_opt_in_and_profiles_do_not_widen_or_accept_server_configuration(self):
        self.assertNotIn("mcp_project_read", Tools(self.policy).registry)
        for config in ({"command": "python"}, {"url": "http://localhost"},
                       {"project_read": 1}, {"timeout_seconds": True}, {"timeout_seconds": 31}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                settings({"mcp": config})
        self.config["mcp"] = {"project_read": True}
        for profile in ("coding", "unified", "browser", "desktop"):
            tools = Tools(self.policy, profile=profile)
            self.addCleanup(tools.close)
            names = {s["function"]["name"] for s in tools.schemas}
            self.assertEqual("mcp_project_read" in names, profile in {"coding", "unified"})
            if profile in {"browser", "desktop"}:
                self.assertEqual(tools.execute("mcp_project_read", {"path": "x"})["error"], "Denied")
            self.assertEqual(tools.execute("mcp_project_read", {"path": "x", "command": "echo"})["error"],
                             "TypeError" if profile in {"coding", "unified"} else "Denied")

    def test_scope_credentials_state_links_and_large_files_fail_before_spawn(self):
        self.config["mcp"] = {"project_read": True}
        provider = ProjectProvider(self.policy)
        (self.policy.root / "large.txt").write_bytes(b"x" * 8193)
        self.policy.state = self.policy.root / "private"
        self.policy.state.mkdir()
        (self.policy.state / "data.txt").write_text("private")
        (self.policy.root / "code.txt").write_text("ok")
        os.link(self.policy.root / "code.txt", self.policy.root / "link.txt")
        with patch("local_agent.mcp_process.subprocess.Popen") as spawn:
            for path in ("../escape", "C:\\secret", ".env.local", ".npmrc", ".git/config",
                         "private/data.txt", "node_modules/a.js", "large.txt", "link.txt"):
                with self.subTest(path=path), self.assertRaises((Denied, ValueError)):
                    provider.read(path)
            spawn.assert_not_called()

    def test_strict_read_has_exact_byte_hash_and_redacts_before_transmission(self):
        import hashlib
        raw = 'hello \u4e16\u754c\r\nAPI_KEY=fixture-super-secret\n'.encode()
        (self.policy.root / "code.txt").write_bytes(raw)
        result = read_text(self.policy, "code.txt")
        self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["bytes"], len(raw))
        self.assertNotIn("fixture-super-secret", result["text"])
        self.assertIn("\r\n", result["text"])
        for raw in (b"\xff", b"\0", b"x" * 8193):
            (self.policy.root / "code.txt").write_bytes(raw)
            with self.assertRaises((Denied, UnicodeError)):
                read_text(self.policy, "code.txt")

    def test_changed_input_is_rejected_after_read(self):
        path = self.policy.root / "code.txt"
        path.write_text("one")
        original = approved_path
        count = 0

        def change(policy, value):
            nonlocal count
            count += 1
            if count == 2:
                path.write_text("two")
            return original(policy, value)

        with patch("local_agent.mcp_contract.approved_path", change), self.assertRaises(Denied):
            read_text(self.policy, "code.txt")

    def test_missing_sdk_and_frozen_command_are_actionable_and_fixed(self):
        with (patch("local_agent.mcp_provider.version", return_value="0"),
              self.assertRaisesRegex(MCPError, "mcp==2.3.0")):
            require_sdk()
        with patch.object(sys, "frozen", True, create=True):
            self.assertEqual(server_command(self.policy)[:2], [sys.executable, "--mcp-project-server"])


@skipUnless(HAS_MCP, "Install the pinned mcp extra for real SDK/stdio acceptance")
class MCPIntegrationTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        require_sdk()
        self.config["mcp"] = {"project_read": True, "timeout_seconds": 5}
        self.file = self.policy.root / "code.txt"
        self.file.write_bytes(b"hello MCP\n")
        self.provider = ProjectProvider(self.policy)
        self.addCleanup(self.provider.close)

    def fixture(self, mode):
        return patch("local_agent.mcp_provider.server_command", return_value=[sys.executable, "-I",
                     str(Path(__file__).with_name("mcp_fixture.py").resolve()), mode, str(self.policy.state)])

    def assert_dead(self, name):
        import psutil
        pid = int((self.policy.state / name).read_text())
        deadline = time.monotonic() + 2
        while psutil.pid_exists(pid) and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(psutil.pid_exists(pid), f"Owned MCP process {pid} survived")

    def test_real_handshake_list_call_audit_and_cleanup(self):
        tools = Tools(self.policy, profile="coding")
        self.addCleanup(tools.close)
        calls, original = [], subprocess.Popen

        def spawn(*args, **kwargs):
            proc = original(*args, **kwargs)
            calls.append(proc)
            return proc

        with patch("local_agent.mcp_process.subprocess.Popen", spawn):
            result = tools.execute("mcp_project_read", {"path": "code.txt"})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["untrusted_data"]["text"], "hello MCP\n")
        self.assertEqual(result["untrusted_data"]["provider"], "local-work-agent-project")
        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(calls[0].poll())
        records = [json.loads(x) for x in (self.policy.state / "audit.jsonl").read_text().splitlines()]
        self.assertEqual([r["status"] for r in records], ["attempt", "ok"])
        self.assertNotIn("hello MCP", json.dumps(records))
        self.assertFalse(self.approvals)

    def test_identity_schema_description_extra_tools_and_pagination_need_review(self):
        for mode in ("identity", "schema", "description", "extra", "paged"):
            with self.subTest(mode=mode), self.fixture(mode), self.assertRaises(MCPReviewRequired):
                self.provider.read("code.txt")
            self.assertFalse((self.policy.state / "called").exists())
            self.assert_dead("server.pid")

    def test_invalid_oversized_partial_unexpected_disconnect_and_forged_result_fail_closed(self):
        for mode in ("oversize", "partial", "invalid", "request", "disconnect", "bad_result"):
            with self.subTest(mode=mode), self.fixture(mode), self.assertRaises(MCPError) as raised:
                self.provider.read("code.txt")
            self.assertNotIn("fixture-secret", str(raised.exception))
            self.assert_dead("server.pid")

    def test_timeout_during_handshake_or_tool_closes_server(self):
        self.provider.timeout = 2
        for mode in ("hang_init", "hang"):
            start = time.monotonic()
            with self.subTest(mode=mode), self.fixture(mode), self.assertRaises((TimeoutError, MCPError)):
                self.provider.read("code.txt")
            self.assertLess(time.monotonic() - start, 6)
            self.assert_dead("server.pid")

    def test_cancel_reaps_descendant_and_preserves_unrelated_process(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"],
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.addCleanup(unrelated.wait)
        self.addCleanup(unrelated.kill)
        outcomes = []

        def run():
            try:
                self.provider.read("code.txt")
            except BaseException as exc:  # noqa: BLE001 -- assert cancellation type across test thread
                outcomes.append(exc)

        with self.fixture("child"):
            thread = threading.Thread(target=run)
            thread.start()
            self.addCleanup(thread.join, 10)
            deadline = time.monotonic() + 8
            while not (self.policy.state / "waiting").exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue((self.policy.state / "waiting").exists())
            self.policy.stop_event.set()
            thread.join(6)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 1)
        self.assertIsInstance(outcomes[0], Stopped)
        self.assert_dead("server.pid")
        self.assert_dead("child.pid")
        self.assertIsNone(unrelated.poll())

    def test_server_independently_rejects_out_of_scope_and_unknown_tools(self):
        import anyio
        from mcp import ClientSession

        from local_agent.mcp_provider import transport

        async def exercise():
            async with transport(server_command(self.policy), Path(__file__).parent.parent) as streams:  # noqa: SIM117 -- session needs streams
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    for tool, args in (("read_text", {"path": "../escape"}),
                                       ("read_text", {"path": ".env"}), ("shell", {"path": "code.txt"})):
                        result = await session.call_tool(tool, args)
                        self.assertTrue(result.is_error)
        anyio.run(exercise)

    def test_server_does_not_inherit_application_secret(self):
        from local_agent.process import environment
        with patch.dict(os.environ, {"MCP_TEST_SECRET": "fixture-super-secret"}):
            self.assertNotIn("MCP_TEST_SECRET", environment())
            with self.fixture("secret"), self.assertRaises(MCPError):
                self.provider.read("code.txt")
        self.assert_dead("server.pid")

    def test_close_interrupts_blocked_call_and_does_not_allow_a_second_read(self):
        outcomes = []

        def run():
            try:
                self.provider.read("code.txt")
            except BaseException as exc:  # noqa: BLE001 -- cross-thread cancellation assertion
                outcomes.append(exc)

        with self.fixture("hang"):
            thread = threading.Thread(target=run)
            thread.start()
            self.addCleanup(thread.join, 8)
            deadline = time.monotonic() + 8
            while not (self.policy.state / "waiting").exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue((self.policy.state / "waiting").exists())
            self.provider.close()
            thread.join(6)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(outcomes[0], Stopped)
        self.assert_dead("server.pid")
        with self.assertRaises(Denied):
            self.provider.read("code.txt")

    def test_job_or_resume_failure_prevents_server_execution_and_closes_process(self):
        from local_agent.mcp_process import start
        if os.name != "nt":
            self.skipTest("Windows suspended-spawn ownership boundary")
        for target in ("local_agent.windows_job.WindowsJob", "local_agent.mcp_process.resume_owned"):
            with (self.subTest(target=target), patch(target, side_effect=OSError("fixture")),
                  self.assertRaises(OSError)):
                start([sys.executable, "-I", str(Path(__file__).with_name("mcp_fixture.py")),
                       "hang_init", str(self.policy.state)], Path(__file__).parent.parent)
            self.assertFalse((self.policy.state / "server.pid").exists())


@skipUnless(HAS_MCP, "Install the pinned mcp extra for real SDK/worker acceptance")
class MCPProcessTests(StudioProcessFixture, WorkspaceTest):
    def test_real_worker_uses_selected_project_and_persists_tool_journal(self):
        from http.server import BaseHTTPRequestHandler

        from .ollama_fixture import serve_metadata

        self.config["mcp"] = {"project_read": True}
        for name in ("first", "second"):
            (self.policy.root / name).mkdir()
            (self.policy.root / name / "code.txt").write_text(name)

        class Protocol(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if not serve_metadata(self):
                    self.send_error(404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if serve_metadata(self, body):
                    return
                if body.get("format"):
                    message = {"content": '{"steps":["Read approved project through MCP"]}'}
                elif any(m["role"] == "tool" for m in body["messages"]):
                    message = {"content": "Observed project data"}
                else:
                    message = {"tool_calls": [{"function": {
                        "name": "mcp_project_read", "arguments": {"path": "code.txt"}}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"message": {"role": "assistant", **message},
                                            "done": True, "done_reason": "stop"}).encode())

        self.server.RequestHandlerClass = Protocol
        task = self.manager.start(self.conversation, "Read approved project", "agent", "fixture",
                                  project="first", profile="coding")
        self.wait_until(lambda: not self.manager.running)
        events = [e for e in self.manager.store.events() if e["kind"] == "tool_result"]
        self.assertEqual(len(events), 1)
        result = events[0]["payload"]["result"]
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["untrusted_data"]["text"], "first")
        self.assertEqual(self.manager.tasks()[0]["status"], "reported")
        self.assertFalse(self.manager.pending())
        self.assertFalse(self.manager.store.verifications(task))
        journal = self.manager.store.journal(task)
        self.assertEqual([(op["tool"], op["effect"], op["state"]) for op in journal["operations"]],
                         [("mcp_project_read", "read", "completed")])


@skipUnless(HAS_MCP and os.getenv("FROZEN_BACKEND_TEST_EXE"), "Build/select a frozen MCP backend")
class FrozenMCPTests(WorkspaceTest):
    def test_actual_frozen_stdio_server_works_without_external_python(self):
        self.config["mcp"] = {"project_read": True}
        (self.policy.root / "code.txt").write_bytes(b"frozen MCP\n")
        argv = [str(Path(os.environ["FROZEN_BACKEND_TEST_EXE"]).resolve()), "--mcp-project-server",
                "--root", str(self.policy.root), "--state", str(self.policy.state)]
        with patch("local_agent.mcp_provider.server_command", return_value=argv):
            provider = ProjectProvider(self.policy)
            self.addCleanup(provider.close)
            result = provider.read("code.txt")
        self.assertEqual(result["text"], "frozen MCP\n")


@skipUnless(HAS_MCP and os.getenv("LIVE_MCP") == "1", "Actual local-model/MCP workflow is opt-in")
class LiveMCPTests(WorkspaceTest):
    def test_local_model_uses_real_mcp_provider_and_persists_evidence(self):
        from local_agent.studio.manager import Manager

        self.config["mcp"] = {"project_read": True}
        (self.policy.root / "code.txt").write_bytes(b"Local MCP acceptance fixture\n")
        manager = Manager(self.config)
        self.addCleanup(manager.close)
        conversation = manager.store.conversation()
        task = manager.start(conversation,
            "Use only the mcp_project_read tool to read code.txt once. "
            "Then report its text. Do not use read_file or other tools.",
            "agent", self.config["model"]["name"], profile="coding")
        deadline = time.monotonic() + 120
        while manager.running and time.monotonic() < deadline:
            time.sleep(.1)
        self.assertFalse(manager.running, "Actual-model MCP workflow did not finish")
        events = [e for e in manager.store.events() if e["kind"] == "tool_result"]
        self.assertTrue(events, manager.tasks()[0]["result"])
        self.assertTrue(any(e["payload"]["result"].get("untrusted_data", {}).get("provider")
                            == "local-work-agent-project" and e["payload"]["result"]["ok"]
                            for e in events), events)
        self.assertEqual(manager.tasks()[0]["status"], "reported")
        self.assertTrue(any(op["tool"] == "mcp_project_read" and op["state"] == "completed"
                            for op in manager.store.journal(task)["operations"]))
