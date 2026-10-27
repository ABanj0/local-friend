"""Real SQLite and loopback delivery/restart/flow-control acceptance."""
import json
import time
import unittest

from local_agent.studio.event_stream import ACK_TIMEOUT, PAGE_BYTES, PAGE_SIZE
from local_agent.studio.store import Store

from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


def seed_events(store, task, count):
    with store.connection() as db:
        db.executemany("INSERT INTO events(task,kind,payload,created) VALUES (?,'progress',?,?)",
                       ((task, json.dumps({"marker": n}), time.time()) for n in range(count)))


class EventStoreTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.store = Store(self.policy.state / "studio.sqlite3")
        self.conversation = self.store.conversation()
        self.task = self.store.task(self.conversation, "chat", "fixture")

    def test_5001_events_are_paged_to_captured_boundary(self):
        seed_events(self.store, self.task, 5001)
        through = self.store.event_high_water()
        self.store.event(self.task, "progress", {"new": True})
        cursor, seen = 0, []
        while cursor < through:
            page = self.store.event_page(cursor, through)
            self.assertLessEqual(len(page), PAGE_SIZE)
            self.assertLess(len(json.dumps(page).encode()), PAGE_BYTES)
            seen.extend(row["seq"] for row in page)
            cursor = page[-1]["seq"] if page else through
        self.assertEqual(seen, list(range(1, 5002)))
        self.assertEqual(self.store.event_page(cursor, self.store.event_high_water())[0]["seq"], 5002)

    def test_deleted_rows_never_rewind_the_cursor_or_store_identity(self):
        seed_events(self.store, self.task, 5)
        identity = self.store.identity
        self.store.delete_conversation(self.conversation)
        restarted = Store(self.store.path)
        self.assertEqual(restarted.identity, identity)
        self.assertEqual(restarted.event_high_water(), 5)
        self.assertEqual(restarted.event_page(0, 5), [])
        self.assertNotEqual(Store(self.policy.state / "other.sqlite3").identity, identity)

    def test_byte_budget_and_intentional_transient_storage(self):
        for _ in range(3):
            self.store.event(self.task, "progress", {"text": "x" * (PAGE_BYTES // 2)})
        self.assertEqual(len(self.store.event_page(0, 3)), 1)
        for kind in ("approval", "preview"):
            self.store.event(self.task, kind, {"secret": "TRANSIENT-BODY-CANARY"})
        self.assertEqual([row["payload"] for row in self.store.event_page(3, 5)],
                         [{"transient": True}, {"transient": True}])
        self.assertNotIn(b"TRANSIENT-BODY-CANARY", self.store.path.read_bytes())


@unittest.skipUnless(HAS_SOCKET, "Requires Studio API and WebSocket dependencies")
class EventReplayTests(StudioSocketFixture, WorkspaceTest):
    def authenticate(self, socket, after=0, store_id=None):
        socket.send(json.dumps({"token": self.token, "after": after, "store_id": store_id}))

    def receive(self, socket, ack=True):
        packet = json.loads(socket.recv(timeout=3))
        if ack:
            socket.send(json.dumps({"ack": packet["delivery"]}))
        return packet

    def drain(self, socket):
        events, packets = [], []
        while True:
            packet = self.receive(socket)
            packets.append(packet)
            events.extend(packet["payload"].get("events", []))
            if packet["kind"] == "ready":
                return events, packets

    def test_5001_replay_disconnect_overlap_and_backend_restart(self):
        seed_events(self.store, self.task, 5001)
        with self.connect() as socket:
            self.authenticate(socket)
            first = self.receive(socket, ack=False)
            accepted = {row["seq"]: row for row in first["payload"]["events"]}
            self.assertEqual(len(accepted), PAGE_SIZE)
            # Disconnect after accepting a page but before acknowledging it.
        with self.connect() as socket:
            self.authenticate(socket, 0, self.store.identity)
            events, packets = self.drain(socket)
            for event in events:
                accepted.setdefault(event["seq"], event)
            self.assertEqual(list(accepted), list(range(1, 5002)))
            self.assertEqual([event["seq"] for event in events], list(range(1, 5002)))
            self.assertGreater(len(packets), 25)
            epoch = packets[0]["payload"]["epoch"]
        self.stop_backend()
        self.start_backend()
        with self.connect() as socket:
            self.authenticate(socket, 5001, self.store.identity)
            events, packets = self.drain(socket)
            self.assertEqual(events, [])
            self.assertEqual(packets[0]["payload"]["store_id"], self.store.identity)
            self.assertNotEqual(packets[0]["payload"]["epoch"], epoch)
            self.store.event(self.task, "progress", {"marker": "after-restart"})
            next_packet = self.receive(socket)
            self.assertEqual(next_packet["payload"]["events"][0]["seq"], 5002)
        self.assertTrue(self.http("/health")["ready"])

    def test_captured_boundary_excludes_new_events_until_live_catch_up(self):
        seed_events(self.store, self.task, 401)
        with self.connect() as socket:
            self.authenticate(socket)
            first = self.receive(socket, ack=False)
            self.assertEqual(first["payload"]["through"], 401)
            self.store.event(self.task, "progress", {"marker": "concurrent"})
            socket.send(json.dumps({"ack": first["delivery"]}))
            events, packets = self.drain(socket)
            self.assertEqual([e["seq"] for e in first["payload"]["events"] + events], list(range(1, 402)))
            self.assertEqual(packets[-1]["payload"]["cursor"], 401)
            self.assertEqual(self.receive(socket)["payload"]["events"][0]["seq"], 402)

    def test_slow_client_is_bounded_and_can_reconnect(self):
        from websockets.exceptions import ConnectionClosedError
        seed_events(self.store, self.task, 5001)
        with self.connect() as socket:
            self.authenticate(socket)
            first = self.receive(socket, ack=False)
            self.assertEqual(len(first["payload"]["events"]), PAGE_SIZE)
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                socket.recv(timeout=0.2)  # No second packet until the first is accepted.
            self.assertTrue(self.http("/health")["ready"])
            with self.assertRaises(ConnectionClosedError) as closed:
                socket.recv(timeout=ACK_TIMEOUT + 3)
            self.assertEqual(closed.exception.rcvd.code, 1013)
            self.assertLess(time.monotonic() - started, ACK_TIMEOUT + 3)
        with self.connect() as socket:
            self.authenticate(socket, first["payload"]["cursor"], self.store.identity)
            remaining, _ = self.drain(socket)
            self.assertEqual([e["seq"] for e in remaining], list(range(201, 5002)))

    def test_bad_acknowledgments_cannot_skip_durable_history(self):
        from websockets.exceptions import ConnectionClosedError
        for reply in ({"ack": True}, {"ack": 2}, {"ack": 0}, {"after": 5001}, [], None):
            with self.subTest(reply=reply), self.connect() as socket:
                self.authenticate(socket)
                self.receive(socket, ack=False)
                socket.send(json.dumps(reply))
                with self.assertRaises(ConnectionClosedError) as closed:
                    socket.recv(timeout=3)
                self.assertEqual(closed.exception.rcvd.code, 1008)
        self.assertTrue(self.http("/health")["ready"])

    def test_database_mismatch_and_ahead_cursor_explicitly_reset(self):
        self.store.event(self.task, "progress", {"marker": "original"})
        for after, identity in ((999, self.store.identity), (1, "0" * 32)):
            with self.subTest(after=after), self.connect() as socket:
                self.authenticate(socket, after, identity)
                events, packets = self.drain(socket)
                self.assertTrue(packets[0]["payload"]["reset"])
                self.assertEqual([e["seq"] for e in events], [1])

    def test_malformed_store_identity_is_denied(self):
        for identity in ([], 1, "x", "z" * 32):
            self.reject(json.dumps({"token": self.token, "store_id": identity}))
