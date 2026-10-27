"""Actual owned children and bounded JSON framing, including malicious/fault responses."""
import json
import multiprocessing
import os
import struct
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

from local_agent.studio import probes
from local_agent.studio.directory_snapshot import observe

from .support import WorkspaceTest


def faulty_child(pipe, fault, entered=None):
    try:
        pipe.recv_bytes(16)
        if entered:
            entered.set()
        if fault == 'oversized':
            pipe.send_bytes(b'x' * (probes.MAX_REPLY + 1))
        elif fault == 'invalid':
            pipe.send_bytes(b'PRIVATE-INVALID-PROBE-CANARY')
        elif fault == 'duplicate':
            pipe.send_bytes(b'{"complete":true,"complete":false}')
        elif fault == 'nonfinite':
            pipe.send_bytes(b'{"count":NaN}')
        elif fault == 'partial':
            # POSIX Connection has a stream length prefix; Windows pipes preserve messages.
            os.write(pipe.fileno(), struct.pack('!i', 100))
            time.sleep(30)
        else:
            time.sleep(30)
    finally:
        pipe.close()


class ProbeTests(WorkspaceTest):
    def test_real_directory_child_returns_private_bounded_observation_only(self):
        (self.policy.root / 'source.py').write_text('PRIVATE-FILE-CONTENT-CANARY')
        expected = observe(self.policy)
        actual = probes.run('directory', {'config': self.config, 'path': '.'}, threading.Event(), timeout=4)
        self.assertEqual(actual['fingerprint'], expected['fingerprint'])
        self.assertEqual(actual['scope'], expected['scope'])
        self.assertEqual(set(actual), {'scope', 'fingerprint', 'complete', 'stop_reason', 'counts'})
        self.assertTrue(actual['complete'])
        self.assertNotIn('source.py', json.dumps(actual))
        self.assertNotIn('PRIVATE-', json.dumps(actual))

    def test_invalid_kind_payload_and_deadline_fail_before_any_process(self):
        with patch.object(probes.multiprocessing, 'get_context', side_effect=AssertionError('No spawn for invalid arguments')):
            for kind, payload, timeout in [('command', {}, 1), ('directory', [], 1), ('model', {}, True),
                                           ('directory', {}, float('nan')), ('directory', {}, 9)]:
                with self.subTest(kind=kind, timeout=timeout), self.assertRaises(ValueError):
                    probes.run(kind, payload, threading.Event(), timeout=timeout)

    def test_malformed_and_oversized_real_child_frames_fail_without_leaking_data(self):
        context = multiprocessing.get_context('spawn')
        for fault in ('invalid', 'oversized', 'duplicate', 'nonfinite'):
            def factory(*, target, args, fault=fault):
                return context.Process(target=faulty_child, args=(args[0], fault))

            fake = SimpleNamespace(Pipe=context.Pipe, Process=factory)
            with patch.object(probes.multiprocessing, 'get_context', return_value=fake), self.assertRaises(ValueError) as error:
                probes.run('directory', {}, threading.Event(), timeout=4)
            self.assertNotIn('PRIVATE-', str(error.exception))

    def test_cancel_interrupts_real_waiting_child_and_reaps_only_owned_process(self):
        import psutil
        context = multiprocessing.get_context('spawn')
        entered = context.Event()
        cancelled = threading.Event()
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(45)'])

        def close():
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(3)

        self.addCleanup(close)
        before = {child.pid for child in psutil.Process().children()}
        errors = []

        def factory(*, target, args):
            return context.Process(target=faulty_child, args=(args[0], 'stall', entered))

        def execute():
            try:
                probes.run('directory', {}, cancelled, timeout=8)
            except ValueError as error:
                errors.append(str(error))

        fake = SimpleNamespace(Pipe=context.Pipe, Process=factory)
        with patch.object(probes.multiprocessing, 'get_context', return_value=fake):
            thread = threading.Thread(target=execute)
            thread.start()
            try:
                self.assertTrue(entered.wait(4))
            finally:
                cancelled.set()
                thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertEqual({child.pid for child in psutil.Process().children()} - before, set())
        self.assertIsNone(unrelated.poll())

    def test_reader_start_failure_reaps_child_before_any_observation(self):
        import psutil
        before = {child.pid for child in psutil.Process().children()}
        with patch.object(probes.threading.Thread, 'start', side_effect=RuntimeError('Injected reader start failure')), self.assertRaises(RuntimeError):
            probes.run('directory', {'config': self.config, 'path': '.'}, threading.Event())
        self.assertEqual({child.pid for child in psutil.Process().children()} - before, set())

    def test_closed_reader_race_returns_fixed_error_and_closes_real_pipe_ends(self):
        context = multiprocessing.get_context('spawn')
        parent, child = context.Pipe()
        wrapped = Mock(wraps=parent)
        wrapped.recv_bytes.side_effect = TypeError('PRIVATE-PIPE-CANARY')
        fake = SimpleNamespace(Pipe=lambda: (wrapped, child), Process=context.Process)
        with patch.object(probes.multiprocessing, 'get_context', return_value=fake), self.assertRaises(ValueError) as error:
            probes.run('directory', {'config': self.config, 'path': '.'}, threading.Event(), timeout=4)
        self.assertNotIn('PRIVATE-', str(error.exception))
        self.assertTrue(parent.closed and child.closed)

    def test_incomplete_transport_frame_cannot_hold_parent_past_deadline(self):
        context = multiprocessing.get_context('spawn')
        fault = 'partial' if os.name != 'nt' else 'stall'

        def factory(*, target, args):
            return context.Process(target=faulty_child, args=(args[0], fault))

        fake = SimpleNamespace(Pipe=context.Pipe, Process=factory)
        started = time.monotonic()
        with patch.object(probes.multiprocessing, 'get_context', return_value=fake), self.assertRaises(ValueError):
            probes.run('directory', {}, threading.Event(), timeout=.5)
        self.assertLess(time.monotonic() - started, 4)
