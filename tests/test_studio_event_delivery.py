"""Delivery boundary fixtures: real Manager/SQLite/ASGI, no inference claims."""
import asyncio
import time
import unittest
from unittest.mock import patch

from local_agent.studio.event_stream import MAX_FRAME_BYTES, EventStream

from .studio_support import HAS_API, StudioAPIFixture
from .support import WorkspaceTest


@unittest.skipUnless(HAS_API, "Requires Studio API dependencies")
class EventDeliveryTests(StudioAPIFixture, WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.manager = self.client.app.state.manager
        self.conversation = self.manager.store.conversation()
        self.task = self.manager.store.task(self.conversation, "chat", "delivery-fixture")
        self.addCleanup(self.manager.running.clear)

    def socket(self):
        return self.client.websocket_connect("/events", headers={"origin": "http://tauri.localhost"})

    def receive(self, socket):
        packet = socket.receive_json()
        socket.send_json({"ack": packet["delivery"]})
        return packet

    def test_ram_gap_replays_durable_rows_and_reconciles_streams_and_approvals(self):
        state = {"done": False, "stream": "before-gap", "approvals": {}}
        self.manager.running[self.task] = state
        with self.socket() as socket:
            socket.send_json({"token": "x" * 64})
            initial = socket.receive_json()
            # Deliberately overrun the RAM ring while this client withholds ACK.
            for n in range(5001):
                self.manager.emit(self.task, "token", {"text": str(n)})
            state["stream"] = "authoritative accumulated response"
            for n in range(4):
                self.manager.emit(self.task, "progress", {"marker": n})
            approval = {"id": "review", "action": "execute_code", "details": {"argv": ["python"]},
                        "expires": time.time() + 60}
            state["approvals"]["review"] = approval
            self.manager.emit(self.task, "approval", approval)
            self.manager.emit(self.task, "preview", {"image": "PRIVATE-PREVIEW-CANARY"})
            socket.send_json({"ack": initial["delivery"]})
            self.assertEqual(self.receive(socket)["kind"], "ready")
            recovered = self.receive(socket)
            self.assertEqual(recovered["kind"], "snapshot")
            payload = recovered["payload"]
            self.assertEqual(payload["reason"], "ram_gap")
            self.assertEqual(payload["streams"][self.task], state["stream"])
            self.assertEqual(payload["approvals"], [{"task": self.task, **approval}])
            self.assertEqual([e["seq"] for e in payload["events"]], list(range(1, 7)))
            self.assertEqual(payload["events"][-1]["payload"], {"transient": True})
            self.assertEqual(payload["events"][-2]["payload"], {"transient": True})
            self.assertNotIn("PRIVATE-PREVIEW-CANARY", str(payload))
            self.assertEqual(self.receive(socket)["kind"], "ready")
            self.manager.emit(self.task, "token", {"text": " new"})
            self.manager.emit(self.task, "preview", {"image": "current-live-preview"})
            seen = []
            while len(seen) < 2:
                seen.extend(self.receive(socket)["payload"]["events"])
            self.assertEqual([e["kind"] for e in seen], ["token", "preview"])
            self.assertEqual(seen[-1]["payload"]["image"], "current-live-preview")
        self.assertNotIn("token", [e["kind"] for e in self.manager.store.events()])

    def test_ram_byte_limit_and_deleted_chat_accounting(self):
        for _ in range(3):
            self.manager.emit(self.task, "token", {"text": "x" * (9 * 1024**2)})
        self.assertLessEqual(self.manager.live_bytes, 16 * 1024**2)
        self.assertEqual(len(self.manager.live_events), 1)
        response = self.client.post(f"/conversations/{self.conversation}/delete", json={"confirmed": True},
                                    headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.manager.live_events, [])
        self.assertEqual(self.manager.live_sizes, {})
        self.assertEqual(self.manager.live_bytes, 0)

    def test_live_gap_keeps_transient_bodies_and_durable_order(self):
        with self.socket() as socket:
            socket.send_json({"token": "x" * 64})
            self.receive(socket)
            self.receive(socket)  # ready, before any publication
            # Commit outside the RAM ring between normal live publications.
            with self.manager.lock:
                self.manager.emit(self.task, "token", {"text": "first chunk"})
                self.manager.store.event(self.task, "progress", {"marker": "durable-only"})
                self.manager.emit(self.task, "approval", {"id": "live-review", "action": "execute_code"})
                self.manager.emit(self.task, "token", {"text": "second chunk"})
            events = []
            while len(events) < 4:
                events.extend(self.receive(socket)["payload"].get("events", []))
            self.assertEqual([e["kind"] for e in events], ["token", "progress", "approval", "token"])
            self.assertEqual([e["seq"] for e in events], [0, 1, 2, 0])
            self.assertEqual(events[2]["payload"]["id"], "live-review")

    def test_oversized_durable_item_is_explicitly_rejected(self):
        from starlette.websockets import WebSocketDisconnect
        self.manager.store.event(self.task, "progress", {"text": "x" * MAX_FRAME_BYTES})
        with self.socket() as socket:
            socket.send_json({"token": "x" * 64})
            with self.assertRaises(WebSocketDisconnect) as closed:
                socket.receive_json()
            self.assertEqual(closed.exception.code, 1009)
        self.assertEqual(self.manager.store.event_high_water(), 1)


class EventSendBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocked_transport_send_is_cancelled_within_budget(self):
        cancelled = asyncio.Event()

        class BlockedTransport:
            async def send_json(self, packet):
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

        stream = EventStream(BlockedTransport(), None)
        with (patch("local_agent.studio.event_stream.SEND_TIMEOUT", 0.03),
              self.assertRaises(TimeoutError)):
            await stream._send("replay", {})
        self.assertTrue(cancelled.is_set())
