"""Operator harness contracts; fixtures do not certify the native application."""
import hashlib
import json
import os
import runpy
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = runpy.run_path(str(Path('scripts/native-recovery-check.py').resolve()))
Attempts = MODULE['Attempts']
CheckFailed = MODULE['CheckFailed']
PortGuard = MODULE['PortGuard']


class NativeRecoveryCheckTests(unittest.TestCase):
    def test_three_backoffs_follow_observed_exit_and_budget_requires_four_failures(self):
        attempts = Attempts()
        attempts.rows = [{'pid': i + 1, 'began': began, 'ended': end}
                         for i, (began, end) in enumerate(((0, .5), (1.5, 2), (4, 4.5), (8.5, 9)))]
        self.assertEqual(attempts.backoff(), [1, 2, 4])
        attempts.rows[2]['began'] = 3.8
        with self.assertRaises(CheckFailed):
            attempts.backoff()
        attempts.rows.pop()
        with self.assertRaises(CheckFailed):
            attempts.backoff()

    def test_observation_deduplicates_process_identity_and_bounds_new_attempts(self):
        attempts = Attempts()
        born = attempts.wall
        attempts.observe([(11, born)])
        attempts.observe([(11, born)])
        self.assertEqual(len(attempts.rows), 1)
        attempts.observe([])
        self.assertIsNotNone(attempts.rows[0]['ended'])
        for pid in range(12, 16):
            attempts.observe([(pid, born)])
        with self.assertRaises(CheckFailed):
            attempts.observe([(16, born)])
        with self.assertRaises(CheckFailed):
            Attempts().observe([(22, time.time() + 60)])

    def test_guard_is_loopback_exclusive_releases_and_never_reads_requests(self):
        guard = PortGuard(0)
        address = guard.socket.getsockname()
        self.assertEqual(address[0], '127.0.0.1')
        try:
            with socket.socket() as other, self.assertRaises(OSError):
                other.bind(address)
            # A client can send bytes, but the guard has no accept/read/server callback.
            with socket.create_connection(address, timeout=1) as client:
                client.sendall(b'Authorization: Bearer PRIVATE-CANARY\r\n')
        finally:
            guard.close()
        guard.close()
        with socket.socket() as replacement:
            replacement.bind(address)

    def test_existing_studio_refuses_exercise_without_launch_or_port_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            fn = MODULE['run']
            with (patch.dict(fn.__globals__, existing_studio=lambda: True),
                  patch.object(MODULE['ProcessOutput'], 'start') as start,
                  patch.dict(fn.__globals__, PortGuard=lambda: self.fail('must not bind'))):
                report, path = fn(Path(directory), exercise=True)
            self.assertEqual(report['reason'], 'existing_studio_preserved')
            self.assertEqual(report['native_acceptance'], 'not_verified')
            start.assert_not_called()
            self.assertEqual(json.loads(path.read_text())['reason'], report['reason'])
            self.assertNotIn('PRIVATE', path.read_text())

    def test_invalid_duration_creates_no_case_or_process(self):
        with tempfile.TemporaryDirectory() as directory:
            for seconds in (True, 59, 301, float('nan'), '120'):
                with self.assertRaises(ValueError):
                    MODULE['run'](Path(directory), seconds=seconds)
            self.assertFalse((Path(directory) / '.runtime').exists())

    def test_cleanup_failure_still_closes_other_owner_and_exports_no_raw_error(self):
        fn = MODULE['run']
        with tempfile.TemporaryDirectory() as directory:
            with (patch.dict(fn.__globals__, existing_studio=lambda: True),
                  patch.object(MODULE['ProcessOutput'], 'close',
                               side_effect=[OSError('PRIVATE-CLEANUP'), None]) as close):
                report, path = fn(Path(directory), exercise=True)
            self.assertEqual(close.call_count, 2)
            self.assertEqual(report['reason'], 'owned_cleanup_failed')
            self.assertFalse(report['owned_cleanup'])
            self.assertEqual(report['native_acceptance'], 'not_verified')
            self.assertNotIn('PRIVATE', path.read_text())

    def test_disappearing_backend_does_not_invent_a_native_exit(self):
        import psutil
        sample = MODULE['sample']
        child = unittest.mock.Mock()
        child.name.side_effect = psutil.NoSuchProcess(123)
        parent = unittest.mock.Mock()
        parent.children.return_value = [child]
        native = unittest.mock.Mock()
        native.proc.poll.return_value = None
        with patch.object(psutil, 'Process', return_value=parent):
            sample(native, Attempts())

    def test_real_fixture_deadline_reaps_only_owned_tree_and_releases_guard(self):
        from local_agent.studio.process_output import ProcessOutput

        fn = MODULE['run']
        original = ProcessOutput.start
        owners = []
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'],
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guard = PortGuard(0)
            address = guard.socket.getsockname()
            child_file = root / 'owned-child.pid'
            script = ('import subprocess,sys,time;from pathlib import Path;'
                      'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);'
                      f'path=Path({str(child_file)!r});pending=path.with_suffix(".tmp");'
                      'pending.write_text(str(p.pid));pending.replace(path);time.sleep(30)')

            def start(owner, argv, env):
                owners.append(owner)
                if argv[0].endswith('fixture.exe'):
                    return original(owner, [sys.executable, '-c', script], env)
                return original(owner, argv, env)

            def stop_at_deadline(*args, **kwargs):
                deadline = time.monotonic() + 5
                while not child_file.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(child_file.exists())
                raise CheckFailed('observation_deadline')

            try:
                with (patch.dict(fn.__globals__, existing_studio=lambda: False,
                                 installed=lambda root: (root / 'fixture.exe', {}),
                                 PortGuard=lambda: guard, wait_for=stop_at_deadline),
                      patch.object(ProcessOutput, 'start', start)):
                    report, _ = fn(root, exercise=True)
                self.assertEqual(report['reason'], 'observation_deadline')
                self.assertEqual(report['native_acceptance'], 'not_verified')
                self.assertTrue(report['owned_cleanup'])
                self.assertEqual(len(owners), 2)
                self.assertTrue(all(owner.proc.poll() is not None for owner in owners))
                import psutil
                self.assertFalse(psutil.pid_exists(int(child_file.read_text())))
                self.assertIsNone(unrelated.poll())
                with socket.socket() as replacement:
                    replacement.bind(address)
            finally:
                unrelated.terminate()
                unrelated.wait(5)

    def test_readiness_does_not_launch_and_collision_is_not_native_success(self):
        fn = MODULE['run']
        for exercise, collision in ((False, False), (True, True)):
            with tempfile.TemporaryDirectory() as directory:
                guard = unittest.mock.Mock()

                def reserve(collision=collision, guard=guard):
                    if collision:
                        raise OSError('PRIVATE-SOCKET-ERROR')
                    return guard

                with (patch.dict(fn.__globals__, existing_studio=lambda: False,
                                 installed=lambda root: (root / 'not-executed.exe', {}), PortGuard=reserve),
                      patch.object(MODULE['ProcessOutput'], 'start') as start):
                    report, path = fn(Path(directory), exercise=exercise)
                start.assert_not_called()
                self.assertEqual(report['status'], 'blocked' if collision else 'ready')
                self.assertEqual(report['native_acceptance'], 'not_verified')
                self.assertNotIn('PRIVATE', path.read_text())
                if not collision:
                    guard.close.assert_called_once()

    def test_manifest_mismatch_and_linked_executable_fail_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist').mkdir()
            (root / 'dist/release-manifest.json').write_text(json.dumps({
                'expected_nsis_main_payload': {'status': 'predicted', 'bytes': 3, 'sha256': '0' * 64},
                'artifacts': {'dist/agent-backend.exe': {'bytes': 3, 'sha256': '0' * 64}}}))
            installed = root / 'Local Agent Studio'
            installed.mkdir()
            executable = installed / 'local-agent-studio.exe'
            executable.write_bytes(b'exe')
            with patch.dict(os.environ, LOCALAPPDATA=str(root)):
                with self.assertRaises(CheckFailed):
                    MODULE['installed'](root)
                os.link(executable, root / 'alias.exe')
                with self.assertRaises(CheckFailed):
                    MODULE['installed'](root)

    def test_real_regular_exe_hashes_match_manifest_without_permission_bit_guess(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist').mkdir()
            folder = root / 'Local Agent Studio'
            folder.mkdir()
            expected = {'bytes': 3, 'sha256': hashlib.sha256(b'exe').hexdigest()}
            for name in ('local-agent-studio.exe', 'agent-backend.exe'):
                (folder / name).write_bytes(b'exe')
            (root / 'dist/release-manifest.json').write_text(json.dumps({
                'expected_nsis_main_payload': {'status': 'predicted', **expected},
                'artifacts': {'dist/agent-backend.exe': expected}}))
            with patch.dict(os.environ, LOCALAPPDATA=str(root)):
                path, hashes = MODULE['installed'](root)
            self.assertEqual(path, folder / 'local-agent-studio.exe')
            self.assertEqual(set(hashes.values()), {expected['sha256']})

    def test_process_identity_is_not_name_or_pid_alone_and_unrelated_process_survives(self):
        import psutil

        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'],
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            identity = (child.pid, psutil.Process(child.pid).create_time())
            self.assertTrue(MODULE['alive'](identity))
            self.assertFalse(MODULE['alive']((child.pid, identity[1] - 1)))
            self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait(5)
        self.assertFalse(MODULE['alive'](identity))
