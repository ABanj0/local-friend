"""Rendered recovery budget with real backend HTTP/socket state; native IPC is bridged."""
import json
import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


@unittest.skipUnless(HAS_SOCKET and os.getenv("LIVE_STUDIO_UI") == "1", "Rendered recovery UI is opt-in")
class RecoveryUITests(StudioSocketFixture, WorkspaceTest):
    def test_retry_budget_manual_fallback_and_saved_history(self):
        from playwright.sync_api import expect, sync_playwright

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        try:
            server = ThreadingHTTPServer(("127.0.0.1", 1420),
                                         partial(Quiet, directory=str(Path("desktop/dist").resolve())))
        except OSError:
            # Reuse only this project's current Vite source; never stop its user's server.
            with build_opener(ProxyHandler({})).open("http://127.0.0.1:1420/src/App.tsx", timeout=3) as response:
                self.assertIn("bootVersion", response.read().decode())
        else:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            failures = []
            page.on("requestfailed", lambda request: failures.append((request.url, request.failure)))
            page.on("pageerror", lambda error: failures.append(str(error)))
            page.add_init_script("window.testConnection=" + json.dumps({"port": self.port, "token": self.token}) + ";" + """
                window.attempts=[];window.taskPosts=0;
                window.__TAURI_INTERNALS__={invoke:async command=>{
                  if(command==='backend_diagnostics')return 'Fixture: backend dependency unavailable';
                  window.attempts.push({command,time:performance.now()});
                  if(command==='restart_backend')return window.testConnection;
                  throw new Error('Fixture startup failure');
                }};
                const originalFetch=window.fetch;
                window.fetch=(url,options)=>{
                  if(String(url).endsWith('/tasks')&&options?.method==='POST')window.taskPosts++;
                  return originalFetch(url,options);
                };
            """)
            page.goto("http://127.0.0.1:1420")
            try:
                page.wait_for_function("window.attempts.length===4", timeout=20000)
            except Exception:
                print("Recovery attempts:", page.evaluate("window.attempts"))
                print("Rendered text:", page.locator("body").inner_text()[:1000])
                raise
            page.wait_for_timeout(5000)
            attempts = page.evaluate("window.attempts")
            self.assertEqual(len(attempts), 4)
            for index, delay in enumerate((900, 1900, 3900), start=1):
                self.assertGreaterEqual(attempts[index]["time"] - attempts[index-1]["time"], delay)
            expect(page.get_by_text("Backend diagnostics (bounded, redacted)")).to_be_visible()
            page.get_by_role("button", name="Restart backend", exact=True).click()
            try:
                expect(page.locator(".local-status")).to_contain_text("Connected locally", timeout=15000)
            except Exception:
                print("Recovery failures:", failures)
                print("Notice:", page.locator(".notice").all_text_contents())
                print("Attempts:", page.evaluate("window.attempts"))
                raise
            self.assertEqual(page.evaluate("window.attempts.at(-1).command"), "restart_backend")
            self.assertEqual(page.evaluate("window.taskPosts"), 0)
            self.assertEqual(len(self.store.tasks()), 1)
