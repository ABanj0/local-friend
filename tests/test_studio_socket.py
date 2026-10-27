"""Real loopback WebSocket authentication checks; no model or desktop required."""
import json
import os
import socket
import struct
import time
import unittest

from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


@unittest.skipUnless(HAS_SOCKET, "Requires Studio API and WebSocket dependencies")
class StudioSocketTests(StudioSocketFixture, WorkspaceTest):
    def test_history_pages_use_real_authenticated_http_and_preserve_scope(self):
        from urllib.error import HTTPError
        from urllib.parse import urlencode

        chat = self.store.conversation('Paged HTTP')
        foreign = self.store.conversation('Foreign HTTP')
        with self.store.connection() as db:
            for index in range(205):
                db.execute('INSERT INTO messages(id,conversation,role,content,created) VALUES (?,?,?,?,?)',
                           (f'http-{index}', chat, 'user', str(index), index // 9))
        self.store.message(foreign, 'user', 'FOREIGN-HTTP-CANARY')
        path = f'/history/conversations/{chat}/messages'
        first = self.http(path + '?limit=100')
        self.assertEqual([row['content'] for row in first['items']], [str(i) for i in range(105, 205)])
        second = self.http(path + '?' + urlencode({'limit': 100, 'cursor': first['next']}))
        third = self.http(path + '?' + urlencode({'limit': 100, 'cursor': second['next']}))
        self.assertEqual([row['content'] for row in third['items'] + second['items'] + first['items']],
                         [str(i) for i in range(205)])
        self.assertIsNone(third['next'])
        self.assertNotIn('FOREIGN-HTTP-CANARY', json.dumps(first))
        with self.assertRaises(HTTPError) as rejected:
            self.http(f'/history/conversations/{foreign}/messages?' + urlencode({'cursor': first['next']}))
        self.assertEqual(rejected.exception.code, 400)
        for suffix in ('/history/tasks', '/history/conversations', path):
            with self.assertRaises(HTTPError) as denied:
                self.opener.open(f'http://127.0.0.1:{self.port}{suffix}', timeout=3)
            self.assertEqual(denied.exception.code, 401)

    def test_reset_http_clients_leave_backend_and_authenticated_events_healthy(self):
        # Read only a response prefix, then reset TCP while the server is closing it.
        # This exercises real transport cleanup, not a fabricated exception/context.
        for _ in range(40):
            with socket.create_connection(("127.0.0.1", self.port), timeout=3) as peer:
                peer.sendall((f"GET /health HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
                              f"Authorization: Bearer {self.token}\r\nConnection: close\r\n\r\n").encode())
                self.assertTrue(peer.recv(1))
                peer.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                struct.pack("hh" if os.name == "nt" else "ii", 1, 0))
        self.assertTrue(self.http("/health")["ready"])
        with self.connect() as peer:
            peer.send(json.dumps({"token": self.token, "after": 0}))
            frame = json.loads(peer.recv(timeout=3))
            self.assertEqual(frame["kind"], "snapshot")
            peer.send(json.dumps({"ack": frame["delivery"]}))
        # The fixture also asserts no credential leaks or unhandled traceback on shutdown.

    def test_wrong_token_rejected_before_snapshot(self):
        self.reject(json.dumps({"token": "WRONG-AUTH-CANARY"}))

    def test_missing_and_invalid_token_shapes_are_rejected(self):
        for payload in ({}, {"after": 0}, [], None, {"token": None}, {"token": 1}, {"token": []},
                        {"token": "é" * 32}, {"token": "\ud800"}):
            with self.subTest(payload=payload):
                self.reject(json.dumps(payload))

    def test_malformed_json_is_closed_without_snapshot(self):
        for frame in ("", "{", "not-json"):
            with self.subTest(frame=frame):
                self.reject(frame)

    def test_binary_authentication_frame_is_rejected(self):
        self.reject(json.dumps({"token": self.token}).encode())

    def test_missing_authentication_times_out_and_closes(self):
        from websockets.exceptions import ConnectionClosedError
        with self.connect() as socket:
            started = time.monotonic()
            with self.assertRaises(ConnectionClosedError) as closed:
                socket.recv(timeout=8)
            self.assertIsNotNone(closed.exception.rcvd)
            self.assertEqual(closed.exception.rcvd.code, 1008)
            self.assertGreaterEqual(time.monotonic() - started, 4)
            self.assertLess(time.monotonic() - started, 8)
        self.assertTrue(self.http("/health")["ready"])

    def test_invalid_replay_cursors_are_rejected(self):
        for after in ([], {}, None, "0", True, -1, 0.5, 2**63):
            with self.subTest(after=after):
                self.reject(json.dumps({"token": self.token, "after": after}))
        # A valid JSON number beyond Python's integer parsing limit is malformed input too.
        self.reject('{"token":' + json.dumps(self.token) + ',"after":' + "1" * 5000 + '}')

    def test_valid_authentication_and_cursor_boundaries_receive_snapshot(self):
        for after in (0, 2**63 - 1):
            with self.subTest(after=after), self.connect() as socket:
                socket.send(json.dumps({"token": self.token, "after": after}))
                event = json.loads(socket.recv(timeout=3))
                self.assertEqual(event["kind"], "snapshot")
                self.assertEqual(event["payload"]["tasks"][0]["id"], self.task)
                self.assertEqual(event["payload"]["approvals"], [])

    def test_missing_or_forbidden_origin_is_rejected_before_upgrade(self):
        from websockets.exceptions import InvalidStatus
        for origin in (None, "https://attacker.invalid"):
            with (self.subTest(origin=origin), self.assertRaises(InvalidStatus) as rejected,
                  self.connect(origin)):
                self.fail("Forbidden origin was accepted")
            self.assertEqual(rejected.exception.response.status_code, 403)

    def test_disconnect_before_authentication_keeps_backend_healthy(self):
        with self.connect():
            pass
        self.assertTrue(self.http("/health")["ready"])
        self.assertEqual(self.http("/tasks")["tasks"][0]["id"], self.task)
