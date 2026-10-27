"""Server loop ownership: actual TCP, reset cleanup, and unchanged worker policy."""
import asyncio
import os
import socket
import struct
import unittest

from local_agent.studio.runtime import run_server


@unittest.skipUnless(os.name == "nt", "Windows-specific ASGI transport boundary")
class StudioLoopTests(unittest.TestCase):
    def test_server_owns_tcp_loop_and_closes_it_without_changing_default_worker_loop(self):
        policy = asyncio.get_event_loop_policy()
        observed = []
        marker = object()

        class Server:
            async def serve(self, sockets):
                observed.append(asyncio.get_running_loop())
                self.sockets = sockets

        server = Server()
        run_server(server, marker)
        self.assertEqual(server.sockets, [marker])
        self.assertIsInstance(observed[0], asyncio.SelectorEventLoop)
        self.assertTrue(observed[0].is_closed())
        self.assertIs(asyncio.get_event_loop_policy(), policy)
        worker_loop = asyncio.new_event_loop()
        try:
            self.assertIsInstance(worker_loop, asyncio.ProactorEventLoop)
        finally:
            worker_loop.close()

    def test_reset_peer_leaves_listener_usable_and_unrelated_loop_errors_visible(self):
        errors, observations = [], []

        class Paused(asyncio.Protocol):
            def connection_made(self, transport):
                transport.pause_reading()

        class Server:
            async def serve(self, sockets):
                loop = asyncio.get_running_loop()
                loop.set_exception_handler(lambda _loop, context: errors.append(context))
                with socket.socket() as listener:
                    listener.bind(("127.0.0.1", 0))
                    listener.listen()
                    peer = socket.create_connection(listener.getsockname(), timeout=3)
                    accepted, _ = listener.accept()
                    accepted.setblocking(False)
                    transport, _ = await loop.connect_accepted_socket(Paused, accepted)
                    try:
                        peer.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("hh", 1, 0))
                        peer.close()
                        await asyncio.sleep(.05)
                        transport.close()
                        await asyncio.sleep(.05)
                        self.errors_before_control = list(errors)
                        with socket.create_connection(listener.getsockname(), timeout=3):
                            other, _ = listener.accept()
                            other.close()
                        observations.append("listener reusable")
                        # This is a test-only collector, not a production exception filter.
                        # Prove unrelated errors are still delivered through the normal loop hook.
                        loop.call_soon(lambda: 1 / 0)
                        await asyncio.sleep(0)
                    finally:
                        peer.close()
                        transport.close()
                        accepted.close()

        server = Server()
        run_server(server, None)
        self.assertEqual(server.errors_before_control, [])
        self.assertEqual(observations, ["listener reusable"])
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0]["exception"], ZeroDivisionError)
