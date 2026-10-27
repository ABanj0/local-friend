import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

from local_agent.native_diagnostics import (
    EXE,
    MAX_LOG,
    MAX_REPORT,
    ProbeServer,
    classify,
    consume_log,
    diagnose,
)


class NativeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        marker = self.root / "desktop/src-tauri/Cargo.toml"
        marker.parent.mkdir(parents=True)
        marker.write_text('[package]\nname="diagnostic-fixture"\n')

    def binary(self):
        executable = self.root / EXE
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"not executed in unit tests")
        return executable

    def test_gpu_codes_are_content_free_bounded_and_not_inferred_from_other_errors(self):
        text = "password=PRIVATE-CREDENTIAL\nregistry denied result: 5\n"
        self.assertFalse(classify(text)["gpu_access_denied"])
        for code in range(-1073741790, -1073741770):
            text += f"GPU process exited unexpectedly: exit_code={code}\n"
        text += "FATAL GPU process isn't usable. Goodbye.\n"
        result = classify(text)
        self.assertEqual(len(result["gpu_exit_codes"]), 8)
        self.assertEqual(result["gpu_exit_codes"][0]["hex"], "0xc0000022")
        self.assertTrue(result["gpu_access_denied"])
        self.assertTrue(result["gpu_unusable"])
        self.assertNotIn("PRIVATE-CREDENTIAL", json.dumps(result))
        self.assertNotIn("registry", json.dumps(result))

    def test_invalid_and_truncated_numeric_fields_cannot_create_an_observation(self):
        for field in ("999999999999999", "True", "-1073741790secret", "2147483648"):
            self.assertEqual(classify("GPU process exited unexpectedly: exit_code=" + field)
                             ["gpu_exit_codes"], [])
        result = classify("GPU process exited unexpectedly: exit_code=-1073", truncated=True)
        self.assertEqual(result["gpu_exit_codes"], [])

    def test_only_expected_regular_log_is_removed_and_profile_files_are_preserved(self):
        case = self.root / "case"
        case.mkdir()
        log = case / "webview.log"
        profile = case / "unknown-profile-file"
        profile.write_bytes(b"keep")
        log.write_text("password=PRIVATE\nGPU process exited unexpectedly: exit_code=-1073741790\n")
        result = consume_log(self.root, log)
        self.assertTrue(result["gpu_access_denied"])
        self.assertTrue(result["raw_log_removed"])
        self.assertFalse(log.exists())
        self.assertEqual(profile.read_bytes(), b"keep")
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_oversized_log_has_explicit_truncation_and_bounded_observations(self):
        log = self.root / "webview.log"
        log.write_bytes(b"password=PRIVATE\n" + b"x" * (MAX_LOG + 10))
        result = consume_log(self.root, log)
        self.assertTrue(result["input_truncated"])
        self.assertLess(len(json.dumps(result)), 1024)
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_hardlinked_log_is_never_read_or_deleted(self):
        source, log = self.root / "source", self.root / "webview.log"
        source.write_bytes(b"preserve")
        os.link(source, log)
        with self.assertRaises(ValueError):
            consume_log(self.root, log)
        self.assertEqual(source.read_bytes(), b"preserve")
        self.assertTrue(log.exists())

    def test_bad_duration_cannot_spawn_or_create_a_case(self):
        for seconds in (False, 0, 31, 1.5, "10"):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                diagnose(self.root, seconds)
        self.assertFalse((self.root / ".runtime").exists())

    def test_missing_build_and_existing_studio_never_start_a_process(self):
        with patch("local_agent.native_diagnostics.ProcessOutput.start") as start:
            result, path = diagnose(self.root, 1)
            self.assertEqual(result["reason"], "missing_native_debug_build")
            self.assertEqual(json.loads(path.read_text())["native_acceptance"], "not_verified")
            self.binary()
            with patch("local_agent.native_diagnostics.existing_studio", return_value=True):
                result, other = diagnose(self.root, 1)
            self.assertEqual(result["reason"], "existing_studio_preserved")
            self.assertNotEqual(path.parent, other.parent)
            start.assert_not_called()

    def test_existing_backend_and_frontend_ports_are_preserved(self):
        self.binary()
        with (patch("local_agent.native_diagnostics.existing_studio", return_value=False),
              patch("local_agent.native_diagnostics.ProcessOutput.start") as start):
            with patch("local_agent.native_diagnostics.listening", return_value=True):
                result, _ = diagnose(self.root, 1)
            self.assertEqual(result["reason"], "existing_backend_preserved")
            with (patch("local_agent.native_diagnostics.listening", return_value=False),
                  patch("local_agent.native_diagnostics.ProbeServer", side_effect=OSError("PRIVATE"))):
                result, _ = diagnose(self.root, 1)
            self.assertEqual(result["reason"], "frontend_port_unavailable")
            self.assertNotIn("PRIVATE", json.dumps(result))
            start.assert_not_called()

    def test_real_probe_server_serves_only_a_harmless_page_and_has_no_submission_route(self):
        server = ProbeServer(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        opener = build_opener(ProxyHandler({}))
        origin = f"http://127.0.0.1:{server.server_port}"
        with opener.open(origin + "/", timeout=2) as response:
            body = response.read().decode()
            self.assertIn("Native diagnostic only", body)
            self.assertNotIn("<script", body)
        self.assertTrue(server.requested.is_set())
        for path in ("/agent.toml", "/../private", "/tasks"):
            with self.assertRaises(HTTPError) as raised:
                opener.open(origin + path, timeout=2)
            self.assertEqual(raised.exception.code, 404)
        with self.assertRaises(HTTPError) as raised:
            opener.open(origin + "/tasks", data=b"{}", timeout=2)
        self.assertEqual(raised.exception.code, 501)

    def test_dripping_headers_cannot_strand_server_shutdown(self):
        server = ProbeServer(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        client = socket.create_connection(("127.0.0.1", server.server_port))
        self.addCleanup(client.close)
        client.sendall(b"GET / HTTP/1.1\r\nX-Test: ")

        def drip():
            for _ in range(20):
                try:
                    client.sendall(b"x")
                except OSError:
                    return
                time.sleep(.05)

        writer = threading.Thread(target=drip, daemon=True)
        writer.start()
        time.sleep(.05)
        start = time.monotonic()
        server.shutdown()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertLess(time.monotonic() - start, 1.2)
        writer.join(2)

    def test_spawn_failure_uses_fixed_report_and_releases_owned_frontend(self):
        self.binary()
        real_server = ProbeServer(0)
        with (patch("local_agent.native_diagnostics.existing_studio", return_value=False),
              patch("local_agent.native_diagnostics.listening", return_value=False),
              patch("local_agent.native_diagnostics.ProbeServer", return_value=real_server),
              patch("local_agent.native_diagnostics.ProcessOutput.start", side_effect=OSError("PRIVATE"))):
            result, path = diagnose(self.root, 1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "diagnostic_failed")
        self.assertTrue(result["owned_closed"])
        self.assertNotIn("PRIVATE", path.read_text())
        self.assertLess(path.stat().st_size, MAX_REPORT)
        self.assertEqual(real_server.fileno(), -1)

    def test_real_deadline_reaps_owned_fixture_tree_keeps_unrelated_and_omits_stdout(self):
        import psutil

        from local_agent.studio.process_output import ProcessOutput

        self.binary()
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"],
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.addCleanup(unrelated.wait)
        self.addCleanup(unrelated.kill)
        original = ProcessOutput.start
        script = r'''import os,subprocess,sys,time
from pathlib import Path
root=Path(os.environ['WEBVIEW2_USER_DATA_FOLDER']).parent
child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
(root/'fixture-child.pid').write_text(str(child.pid))
(root/'unknown.keep').write_text('PRIVATE-PROFILE')
(root/'webview.log').write_text("GPU process exited unexpectedly: exit_code=-1073741790\nGPU process isn't usable. Goodbye.\n")
print('password=PRIVATE-STDOUT',flush=True)
time.sleep(60)
'''

        def fixture(owner, argv, env):
            return original(owner, [sys.executable, "-u", "-c", script], env)

        server = ProbeServer(0)
        with (patch("local_agent.native_diagnostics.existing_studio", return_value=False),
              patch("local_agent.native_diagnostics.listening", return_value=False),
              patch("local_agent.native_diagnostics.ProbeServer", return_value=server),
              patch.object(ProcessOutput, "start", fixture)):
            report, path = diagnose(self.root, 2)
        self.assertTrue(report["owned_closed"])
        self.assertEqual(report["status"], "observed_failure")
        self.assertTrue(report["observations"]["gpu_access_denied"])
        self.assertEqual(report["native_acceptance"], "not_verified")
        self.assertNotIn("PRIVATE", path.read_text())
        self.assertEqual((path.parent / "unknown.keep").read_text(), "PRIVATE-PROFILE")
        self.assertFalse((path.parent / "webview.log").exists())
        child_pid = int((path.parent / "fixture-child.pid").read_text())
        deadline = time.monotonic() + 2
        while psutil.pid_exists(child_pid) and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(psutil.pid_exists(child_pid))
        self.assertIsNone(unrelated.poll())


@unittest.skipUnless(os.getenv("LIVE_NATIVE_DIAGNOSTICS") == "1", "Owned native diagnostic is opt-in")
class LiveNativeDiagnosticTests(unittest.TestCase):
    def test_actual_owned_diagnostic_reports_evidence_without_claiming_native_acceptance(self):
        root = Path(__file__).resolve().parent.parent
        report, path = diagnose(root, 8)
        self.assertNotEqual(report["reason"], "missing_native_debug_build", report)
        self.assertTrue(report["native_launched"], report)
        self.assertIn(report["status"], {"observed_failure", "inconclusive", "frontend_requested"})
        self.assertTrue(report["owned_closed"], report)
        self.assertEqual(report["native_acceptance"], "not_verified")
        self.assertLess(path.stat().st_size, MAX_REPORT)
        if report["observations"]["log_present"]:
            self.assertTrue(report["observations"]["raw_log_removed"], report)
        print("Native diagnostic evidence:", json.dumps({"report": str(path.relative_to(root)),
            "status": report["status"], "gpu_access_denied": report["observations"]["gpu_access_denied"],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}))
