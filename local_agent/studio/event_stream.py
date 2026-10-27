"""Bounded, acknowledged event delivery; replay observations, never tool actions."""
import asyncio
import json
import sqlite3
from contextlib import suppress

PAGE_SIZE = 200
PAGE_BYTES = 256 * 1024
MAX_FRAME_BYTES = 16 * 1024**2
SEND_TIMEOUT = 5
ACK_TIMEOUT = 10


class ProtocolError(Exception):
    pass


class EventStream:
    def __init__(self, socket, manager, after=0, store_id=None):
        self.socket, self.manager = socket, manager
        self.cursor, self.store_id = after, store_id
        self.live_cursor = 0
        self.delivery = 0
        self.incoming = None

    async def _send(self, kind, payload):
        self.delivery += 1
        packet = {"kind": kind, "payload": payload, "delivery": self.delivery}
        if len(json.dumps(packet, ensure_ascii=False).encode("utf-8")) > MAX_FRAME_BYTES:
            raise OverflowError
        await asyncio.wait_for(self.socket.send_json(packet), SEND_TIMEOUT)
        reply = await asyncio.wait_for(self.incoming, ACK_TIMEOUT)
        if (not isinstance(reply, dict) or type(reply.get("ack")) is not int
                or reply["ack"] != self.delivery):
            raise ProtocolError
        self.incoming = asyncio.create_task(self.socket.receive_json())

    async def _replay(self, through):
        while self.cursor < through:
            rows = await asyncio.to_thread(self.manager.store.event_page, self.cursor, through)
            cursor = rows[-1]["seq"] if rows else through
            await self._send("replay", {"events": rows, "after": self.cursor, "cursor": cursor,
                                        "through": through, "epoch": self.manager.event_epoch})
            self.cursor = cursor

    def _capture(self, reason):
        with self.manager.lock:
            if getattr(self.manager, 'restore_pending', None) and self.manager.restore_pending.is_set():
                raise ValueError('Restore requires backend restart')
            store = self.manager.store
            through = store.event_high_water()
            reset = self.cursor > through or self.store_id not in (None, store.identity)
            after = 0 if reset else self.cursor
            rows = store.event_page(after, through)
            return {"tasks": self.manager.activity_tasks(),
                    "approvals": self.manager.pending(),
                    "streams": {task: state["stream"] for task, state in self.manager.running.items()
                                if not state["done"]},
                    "events": rows, "after": after,
                    "cursor": rows[-1]["seq"] if rows else through,
                    "through": through, "live_seq": self.manager.sequence,
                    "store_id": store.identity, "epoch": self.manager.event_epoch,
                    "reset": reset, "reason": reason}

    async def _snapshot(self, reason):
        snapshot = await asyncio.to_thread(self._capture, reason)
        await self._send("snapshot", snapshot)
        self.cursor = snapshot["cursor"]
        self.live_cursor = snapshot["live_seq"]
        self.store_id = snapshot["store_id"]
        await self._replay(snapshot["through"])
        await self._send("ready", {"cursor": self.cursor, "epoch": self.manager.event_epoch})

    def _window(self):
        with self.manager.lock:
            rows, size, expected = [], 0, self.live_cursor + 1
            for event in self.manager.live_events:
                if event["live_seq"] <= self.live_cursor:
                    continue
                if event["live_seq"] != expected:
                    return None  # Eviction/deletion: explicitly reconcile authoritative state.
                length = self.manager.live_sizes[event["live_seq"]]
                if rows and (len(rows) >= PAGE_SIZE or size + length > PAGE_BYTES):
                    break
                rows.append(event)
                size += length
                expected += 1
            if not rows and self.manager.sequence > self.live_cursor:
                return None
            through = self.manager.store.event_high_water() if not rows else None
            return rows, through

    async def _live(self, rows):
        # Fill durable gaps first without losing
        # transient live approval/preview bodies or duplicating already replayed rows.
        batch, after, cursor = [], self.cursor, self.cursor
        for event in rows:
            if event.get("seq", 0) > cursor + 1:
                if batch:
                    await self._send("live", {"events": batch, "after": after, "cursor": cursor,
                                              "epoch": self.manager.event_epoch})
                    self.cursor = cursor
                    batch = []
                await self._replay(event["seq"] - 1)
                await self._send("ready", {"cursor": self.cursor, "epoch": self.manager.event_epoch})
                after = cursor = self.cursor
            if event.get("seq", 0) and event["seq"] <= cursor:
                self.live_cursor = event["live_seq"]
                continue
            cursor = max(cursor, event.get("seq", 0))
            batch.append(event)
            self.live_cursor = event["live_seq"]
        if batch:
            await self._send("live", {"events": batch, "after": after, "cursor": cursor,
                                      "epoch": self.manager.event_epoch})
            self.cursor = cursor

    async def run(self):
        from starlette.websockets import WebSocketDisconnect

        self.incoming = asyncio.create_task(self.socket.receive_json())
        code = None
        try:
            await self._snapshot("initial")
            while True:
                if getattr(self.manager, 'restore_pending', None) and self.manager.restore_pending.is_set():
                    code = 1012
                    break
                if self.incoming.done():
                    # Disconnects and unsolicited messages must not leave an idle sender.
                    self.incoming.result()
                    raise ProtocolError
                window = await asyncio.to_thread(self._window)
                if window is None:
                    await self._snapshot("ram_gap")
                else:
                    rows, through = window
                    if rows:
                        await self._live(rows)
                    else:
                        if through > self.cursor:
                            await self._replay(through)
                            await self._send("ready", {"cursor": self.cursor, "epoch": self.manager.event_epoch})
                        await asyncio.sleep(0.08)
        except WebSocketDisconnect:
            pass
        except TimeoutError:
            code = 1013  # A slow/unacknowledging peer reconnects from its accepted cursor.
        except (ProtocolError, ValueError, KeyError, TypeError):
            code = 1008
        except OverflowError:
            code = 1009
        except (OSError, sqlite3.Error):
            code = 1011
        finally:
            self.incoming.cancel()
            with suppress(asyncio.CancelledError, WebSocketDisconnect, ValueError, KeyError, TypeError):
                await self.incoming
            if code:
                with suppress(TimeoutError, RuntimeError, WebSocketDisconnect):
                    await asyncio.wait_for(self.socket.close(code=code), 1)
