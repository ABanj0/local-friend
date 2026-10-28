"""Opt-in rendered UI replay against real sockets/SQLite, without model inference."""
import json
import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest
from .test_studio_replay import seed_events


@unittest.skipUnless(HAS_SOCKET and os.getenv("LIVE_STUDIO_UI") == "1",
                     "Set LIVE_STUDIO_UI=1 after building the frontend")
class EventReplayUITests(StudioSocketFixture, WorkspaceTest):
    def test_5001_events_occur_once_in_ui_across_reconnect_and_backend_restart(self):
        from playwright.sync_api import expect, sync_playwright
        root = Path.cwd()
        self.assertTrue((root / "desktop/dist/index.html").exists(), "Build desktop assets first")
        seed_events(self.store, self.task, 5001)

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 1420),
                                     partial(QuietHandler, directory=str(root / "desktop/dist")))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            # Native connection discovery alone is bridged. No REST/event responses
            # are intercepted; the backend process, DB and frontend state are real.
            page.add_init_script("window.testConnection=" + json.dumps({"port": self.port, "token": self.token}) + ";" + """
                window.__TAURI_INTERNALS__={invoke: async command => {
                    if (['backend_connection','restart_backend'].includes(command)) return window.testConnection;
                    throw new Error('Native command unavailable in browser acceptance');
                }};
                window.testSockets=[]; window.testReady=0; window.testSequences=[];
                const OriginalSocket=window.WebSocket;
                window.WebSocket=class extends OriginalSocket {
                    constructor(...args) {
                        super(...args); window.testSockets.push(this);
                        this.addEventListener('message', ({data})=>{
                            const packet=JSON.parse(data);
                            if(packet.kind==='ready')window.testReady++;
                            for(const event of packet.payload.events||[])if(event.seq)window.testSequences.push(event.seq);
                        });
                    }
                };
            """)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:1420")
            page.wait_for_function("window.testReady >= 1")
            page.get_by_role("button", name="WEBSOCKET-PRIVATE-CANARY", exact=True).click()
            selector = page.get_by_label("Activity task", exact=True)
            expect(selector).to_have_value(self.task)
            activity = page.locator(".event-list")
            expect(activity).to_have_attribute("aria-label", "5001 retained activity events for this task", timeout=15000)
            expect(activity).to_contain_text('5000')
            self.assertEqual(page.evaluate("window.testSequences"), list(range(1, 5002)))
            page.evaluate("window.testSockets.at(-1).close()")
            page.wait_for_function("window.testReady >= 2", timeout=15000)
            expect(activity).to_have_attribute("aria-label", "5001 retained activity events for this task")
            self.assertEqual(page.evaluate("window.testSequences"), list(range(1, 5002)))
            self.stop_backend()
            expect(page.get_by_role("button", name="Restart backend")).to_be_visible()
            self.start_backend()
            page.evaluate("value => window.testConnection=value", {"port": self.port, "token": self.token})
            page.get_by_role("button", name="Restart backend").click()
            page.wait_for_function("window.testReady >= 3", timeout=15000)
            expect(selector).to_have_value(self.task)
            expect(activity).to_have_attribute("aria-label", "5001 retained activity events for this task")
            self.store.event(self.task, "progress", {"marker": "AFTER-RESTART-5002"})
            expect(activity).to_have_attribute("aria-label", "5002 retained activity events for this task")
            expect(activity).to_contain_text("AFTER-RESTART-5002")
            self.assertEqual(page.evaluate("window.testSequences"), list(range(1, 5003)))
            self.assertEqual(errors, [])
            page.screenshot(path=str(root / ".runtime/p0-02-replay/ui-restart.png"))
            browser.close()
