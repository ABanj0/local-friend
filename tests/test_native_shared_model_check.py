"""Operator contracts and process fixtures; these do not certify a native window."""
import json
import os
import runpy
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from local_agent.safety import Denied

MODULE = runpy.run_path(str(Path('scripts/native-shared-model-check.py').resolve()))
GLOBALS = MODULE['run'].__globals__
RECOVERY = GLOBALS['RECOVERY']
CheckFailed = MODULE['CheckFailed']


class NativeSharedModelCheckTests(unittest.TestCase):
    def test_existing_service_is_never_started_owned_or_terminated(self):
        model = MODULE['SharedModel']()
        with (patch.dict(GLOBALS, listener=lambda: (123, 1.5), healthy=lambda: True),
              patch.dict(RECOVERY, alive=lambda identity: identity == (123, 1.5)),
              patch.object(model.owner, 'start') as start,
              patch.dict(GLOBALS, launch=Mock(side_effect=AssertionError('must not launch')))):
            model.prepare({}, time.monotonic() + 1)
            model.verify()
            model.close()
        start.assert_not_called()
        self.assertIsNone(model.owner.proc)
        self.assertFalse(model.fixture_started)

    def test_identity_change_dead_service_and_bad_health_fail_closed(self):
        for observed, alive, health in (((123, 2), True, True),
                                        ((123, 1), False, True), ((123, 1), True, False)):
            with self.subTest(observed=observed, alive=alive, health=health):
                model = MODULE['SharedModel']()
                model.identity = (123, 1)
                with (patch.dict(GLOBALS, listener=Mock(return_value=observed),
                                 healthy=Mock(return_value=health)),
                      patch.dict(RECOVERY, alive=Mock(return_value=alive)),
                      self.assertRaisesRegex(CheckFailed, 'independent_model_not_healthy')):
                    model.verify()

    def test_bind_race_never_probes_or_terminates_the_winning_service(self):
        model = MODULE['SharedModel']()
        model.owner = Mock()
        model.owner.proc.pid = os.getpid()
        model.owner.proc.poll.return_value = None
        probe = Mock(side_effect=AssertionError('no HTTP before ownership'))
        with (patch.dict(GLOBALS, listener=Mock(side_effect=[None, (999999, 1)]),
                         launch=lambda _: (['trusted', 'serve'], {}), healthy=probe),
              patch.dict(RECOVERY, descendants=lambda _: [])):
            with self.assertRaisesRegex(CheckFailed, 'model_listener_ownership_changed'):
                model.prepare({}, time.monotonic() + 1)
            model.close()
        model.owner.start.assert_called_once_with(['trusted', 'serve'], {})
        model.owner.close.assert_called_once()
        probe.assert_not_called()

    def test_fixture_exit_and_deadline_never_claim_native_success(self):
        for poll, seconds, reason in ((1, 1, 'model_fixture_exited'),
                                      (None, -1, 'model_start_deadline')):
            model = MODULE['SharedModel']()
            model.owner = Mock()
            model.owner.proc.poll.return_value = poll
            with patch.dict(GLOBALS, listener=lambda: None, launch=lambda _: (['trusted'], {})):
                with self.assertRaisesRegex(CheckFailed, reason):
                    model.prepare({}, time.monotonic() + seconds)
                model.close()
            model.owner.close.assert_called_once()

    def test_listener_requires_literal_loopback_single_owner_and_exact_process(self):
        import psutil
        process = Mock(pid=42)
        process.name.return_value = 'ollama.exe'
        process.create_time.return_value = 1.5

        def row(ip='127.0.0.1', pid=42):
            return Mock(status=psutil.CONN_LISTEN, laddr=Mock(ip=ip, port=11434), pid=pid)

        with (patch.object(psutil, 'net_connections', return_value=[row()]),
              patch.object(psutil, 'Process', return_value=process)):
            self.assertEqual(MODULE['listener'](), (42, 1.5))
        for rows in ([row('0.0.0.0')], [row(), row()], [row(pid=None)]):
            with (patch.object(psutil, 'net_connections', return_value=rows),
                  self.assertRaises(CheckFailed)):
                MODULE['listener']()
        process.name.return_value = 'unrelated.exe'
        with (patch.object(psutil, 'net_connections', return_value=[row()]),
              patch.object(psutil, 'Process', return_value=process), self.assertRaises(CheckFailed)):
            MODULE['listener']()

    def test_configuration_is_read_only_and_rejects_nondefault_or_linked_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'local.agent.studio/agent.toml'
            path.parent.mkdir()
            with patch.dict(os.environ, LOCALAPPDATA=directory):
                for url in ('http://127.0.0.1:11434', 'http://127.0.0.1:11435', 'https://example.org'):
                    raw = f'[model]\nurl = "{url}"\n'.encode()
                    path.write_bytes(raw)
                    if url.endswith(':11434'):
                        self.assertEqual(MODULE['configuration']()['base'], str(path.parent))
                    else:
                        with self.assertRaises(CheckFailed):
                            MODULE['configuration']()
                    self.assertEqual(path.read_bytes(), raw)
                os.link(path, path.with_name('alias.toml'))
                with self.assertRaises(Denied):
                    MODULE['configuration']()

    def test_existing_studio_is_preserved_and_no_owner_or_port_is_started(self):
        with tempfile.TemporaryDirectory() as directory:
            with (patch.dict(RECOVERY, existing_studio=lambda: True,
                             PortGuard=Mock(side_effect=AssertionError('must not bind'))),
                  patch.object(MODULE['ProcessOutput'], 'start') as start):
                report, path = MODULE['run'](Path(directory), exercise=True)
            start.assert_not_called()
            self.assertEqual(report['reason'], 'existing_studio_preserved')
            self.assertEqual(report['native_acceptance'], 'not_verified')
            self.assertTrue(report['owned_cleanup'])
            self.assertEqual(json.loads(path.read_text()), report)

    def test_preflight_validates_launch_but_never_opens_a_window_or_claims_acceptance(self):
        launch = Mock(return_value=(['trusted', 'serve'], {}))
        guard = Mock()
        with tempfile.TemporaryDirectory() as directory:
            with (patch.dict(RECOVERY, existing_studio=lambda: False,
                             installed=lambda _: (Path('unused.exe'), {}), PortGuard=lambda: guard),
                  patch.dict(GLOBALS, configuration=dict, listener=lambda: None, launch=launch),
                  patch.object(MODULE['ProcessOutput'], 'start') as start):
                report, _ = MODULE['run'](Path(directory))
            self.assertEqual(report['status'], 'ready')
            self.assertEqual(report['native_acceptance'], 'not_verified')
            launch.assert_called_once()
            start.assert_not_called()
            guard.close.assert_called_once()

    def test_backend_collision_prevents_starting_either_service(self):
        with (tempfile.TemporaryDirectory() as directory,
              patch.dict(RECOVERY, existing_studio=lambda: False,
                         installed=lambda _: (Path('unused.exe'), {}),
                         PortGuard=Mock(side_effect=OSError('PRIVATE-COLLISION'))),
              patch.dict(GLOBALS, configuration=dict),
              patch.object(MODULE['ProcessOutput'], 'start') as start):
            report, path = MODULE['run'](directory, exercise=True)
            self.assertEqual(report['reason'], 'backend_port_unavailable')
            self.assertEqual(report['native_acceptance'], 'not_verified')
            self.assertNotIn('PRIVATE', path.read_text())
            start.assert_not_called()

    def test_cleanup_failure_cannot_skip_other_owner_or_export_private_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            with (patch.dict(RECOVERY, existing_studio=lambda: True),
                  patch.object(MODULE['ProcessOutput'], 'close',
                               side_effect=[OSError('PRIVATE-CLEANUP'), None]) as close):
                report, path = MODULE['run'](Path(directory), exercise=True)
            self.assertEqual(close.call_count, 2)
            self.assertEqual(report['reason'], 'owned_cleanup_failed')
            self.assertFalse(report['owned_cleanup'])
            self.assertNotIn('PRIVATE', path.read_text())

    def test_invalid_options_create_no_files_or_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            for seconds in (True, 59, 301, '180', float('inf')):
                with self.assertRaises(ValueError):
                    MODULE['run'](directory, seconds=seconds)
            self.assertFalse((Path(directory) / '.runtime').exists())

    def test_success_contract_requires_connection_independence_close_and_health_before_cleanup(self):
        """Exercise orchestration with fixtures, never native acceptance evidence."""
        native = Mock()
        native.proc.pid = 73
        native.proc.poll.return_value = None
        model = Mock(identity=(71, 1), fixture_started=False)
        model.owner.proc = None
        events = []

        def confirm(word, *args, **kwargs):
            events.append(word)
            if word == 'CONNECTED':
                attempts.rows.append({'pid': 72})
            else:
                native.proc.poll.return_value = 0

        def wait_for(predicate, *args, **kwargs):
            self.assertTrue(predicate())
            events.append('owned_exit')

        attempts = Mock(rows=[])
        model.verify.side_effect = lambda: events.append('health')
        model.close.side_effect = lambda: events.append('model_cleanup')
        with (tempfile.TemporaryDirectory() as directory,
              patch.dict(RECOVERY, existing_studio=lambda: False,
                         installed=lambda _: (Path('unused.exe'), {}), PortGuard=Mock(),
                         Attempts=lambda: attempts, confirm=confirm, wait_for=wait_for,
                         owned_listener=lambda _: True, descendants=lambda _: [(72, 2)],
                         alive=lambda _: False),
              patch.dict(GLOBALS, configuration=dict, SharedModel=lambda: model,
                         ProcessOutput=lambda: native)):
            report, _ = MODULE['run'](directory, exercise=True)
        self.assertEqual(events, ['CONNECTED', 'health', 'CLOSED', 'owned_exit', 'health', 'model_cleanup'])
        self.assertEqual(report['status'], 'passed')
        self.assertTrue(report['independent_ollama_same_identity_listener_and_health'])
        self.assertEqual(report['native_acceptance'], 'independent_ollama_normal_close_only')

    def test_missing_owner_confirmation_never_reports_native_success(self):
        model = Mock(identity=(71, 1), fixture_started=False)
        model.owner.proc = None
        native = Mock()
        native.proc.pid = 73
        native.proc.poll.return_value = 0
        with (tempfile.TemporaryDirectory() as directory,
              patch.dict(RECOVERY, existing_studio=lambda: False,
                         installed=lambda _: (Path('unused.exe'), {}), PortGuard=Mock(),
                         confirm=Mock(side_effect=CheckFailed('owner_confirmation_missing'))),
              patch.dict(GLOBALS, configuration=dict, SharedModel=lambda: model,
                         ProcessOutput=lambda: native)):
            report, _ = MODULE['run'](directory, exercise=True)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['native_acceptance'], 'not_verified')
        self.assertEqual(report['reason'], 'owner_confirmation_missing')
        native.close.assert_called_once()
        model.close.assert_called_once()

    def test_real_probe_accepts_only_bounded_version_response_and_never_follows_redirect(self):
        responses = (b'HTTP/1.1 200 OK\r\nContent-Length: 20\r\n\r\n{"version":"0.40.7"}',
                     b'HTTP/1.1 302 Found\r\nLocation: https://example.org\r\nContent-Length: 0\r\n\r\n',
                     b'HTTP/1.1 200 OK\r\nContent-Length: 5000\r\n\r\n' + b'x' * 5000)
        # First JSON body is 20 bytes; exercise a real literal-loopback transport.
        for raw, expected in zip(responses, (True, False, False)):
            with socket.socket() as server:
                server.bind(('127.0.0.1', 0))
                server.listen()
                received = []

                def respond(received=received, raw=raw):
                    connection, _ = server.accept()
                    with connection:
                        received.append(connection.recv(4096))
                        connection.sendall(raw)

                thread = threading.Thread(target=respond, daemon=True)
                thread.start()
                with patch.dict(GLOBALS, PORT=server.getsockname()[1]):
                    self.assertEqual(MODULE['healthy'](), expected)
                thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertIn(b'GET /api/version HTTP/1.1', received[0])
                self.assertNotIn(b'Authorization', received[0])

    def test_real_fixture_cleanup_leaves_independent_process_alive(self):
        from local_agent.studio.process_output import ProcessOutput
        independent = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'],
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        model = MODULE['SharedModel']()
        original = ProcessOutput.start

        def start(owner, argv, env):
            return original(owner, [sys.executable, '-c', 'import time;time.sleep(30)'], env)

        try:
            with (patch.dict(GLOBALS, listener=lambda: None, launch=lambda _: (['fixture'], dict(os.environ))),
                  patch.object(ProcessOutput, 'start', start)):
                with self.assertRaisesRegex(CheckFailed, 'model_start_deadline'):
                    model.prepare({}, time.monotonic() + .15)
                model.close()
            self.assertIsNotNone(model.owner.proc.poll())
            self.assertIsNone(independent.poll())
        finally:
            model.close()
            independent.terminate()
            independent.wait(5)

    def test_model_fixture_ownership_is_checked_before_health_probe(self):
        import psutil
        model = MODULE['SharedModel']()
        model.owner = Mock()
        model.owner.proc.pid = os.getpid()
        model.owner.proc.poll.return_value = None
        expected = (os.getpid(), psutil.Process(os.getpid()).create_time())
        observe = Mock(side_effect=[None, expected, expected, expected])
        probe = Mock(return_value=True)
        with (patch.dict(GLOBALS, listener=observe, launch=lambda _: (['fixture'], {}), healthy=probe),
              patch.dict(RECOVERY, descendants=lambda _: [], alive=lambda _: True)):
            model.prepare({}, time.monotonic() + 1)
            model.close()
        self.assertEqual(model.identity, expected)
        self.assertTrue(model.fixture_started)
        probe.assert_called_once()

    def test_owned_listener_waits_for_health_without_starting_another_process(self):
        import psutil
        model = MODULE['SharedModel']()
        model.owner = Mock()
        model.owner.proc.pid = os.getpid()
        model.owner.proc.poll.return_value = None
        expected = (os.getpid(), psutil.Process(os.getpid()).create_time())
        observed = Mock(side_effect=[None, expected, expected, expected, expected])
        health = Mock(side_effect=[False, False, True])
        with (patch.dict(GLOBALS, listener=observed, launch=lambda _: (['fixture'], {}), healthy=health),
              patch.dict(RECOVERY, descendants=lambda _: [], alive=lambda _: True)):
            model.prepare({}, time.monotonic() + 2)
            model.close()
        self.assertEqual(health.call_count, 3)
        model.owner.start.assert_called_once()
        self.assertEqual(model.identity, expected)

    def test_owned_health_deadline_and_identity_change_never_retry_another_listener(self):
        import psutil
        expected = (os.getpid(), psutil.Process(os.getpid()).create_time())
        for changed in (False, True):
            model = MODULE['SharedModel']()
            model.owner = Mock()
            model.owner.proc.pid = os.getpid()
            model.owner.proc.poll.return_value = None
            sequence = iter([None, expected])

            def observe(changed=changed, sequence=sequence):
                return next(sequence, (999999, 1) if changed else expected)

            health = Mock(return_value=False)
            with (patch.dict(GLOBALS, listener=observe, launch=lambda _: (['fixture'], {}), healthy=health),
                  patch.dict(RECOVERY, descendants=lambda _: [], alive=lambda _: True)):
                reason = 'model_listener_ownership_changed' if changed else 'model_health_deadline'
                with self.assertRaisesRegex(CheckFailed, reason):
                    model.prepare({}, time.monotonic() + .15)
                model.close()
            model.owner.start.assert_called_once()
            if changed:
                self.assertEqual(health.call_count, 1)

    def test_dripping_headers_cannot_extend_health_deadline(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            server.listen()

            def drip():
                connection, _ = server.accept()
                with connection:
                    connection.recv(4096)
                    try:
                        for byte in b'HTTP/1.1 200 OK\r\nX-Test: ' + b'x' * 80:
                            connection.sendall(bytes([byte]))
                            time.sleep(.05)
                    except OSError:
                        pass

            thread = threading.Thread(target=drip, daemon=True)
            thread.start()
            started = time.monotonic()
            with patch.dict(GLOBALS, PORT=server.getsockname()[1]):
                self.assertFalse(MODULE['healthy']())
            self.assertLess(time.monotonic() - started, 3.5)
            thread.join(2)
            self.assertFalse(thread.is_alive())
