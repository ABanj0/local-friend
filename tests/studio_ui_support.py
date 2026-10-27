"""Shared real UI scenario harness; native connection IPC alone is bridged."""
import json
import os
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen


class StudioUIFixture:
    def additional_ui_checks(self, page):
        pass

    def run_chat_attachment_management(self):
        from playwright.sync_api import expect, sync_playwright
        root = Path.cwd()
        if not (root / "desktop/dist/index.html").exists():
            self.fail("Build desktop assets before running UI acceptance")
        config = Path(self.temp.name) / "agent.toml"
        config.write_text((root / "agent.toml").read_text(), encoding="utf-8")
        token = "isolated-ui-test-session-" * 3
        proc = subprocess.Popen([sys.executable, "-m", "local_agent.studio.runtime", "--config", str(config), "--port", "0"],
                                env=dict(os.environ, LOCAL_AGENT_STUDIO_TOKEN=token), text=True,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def cleanup():
            if proc.poll() is None:
                proc.stdin.write("shutdown\n")
                proc.stdin.flush()
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(5)
            from local_agent.safety import redact
            diagnostics = root / ".runtime/ui-diagnostics"
            diagnostics.mkdir(parents=True, exist_ok=True)
            (diagnostics / (self._testMethodName + ".log")).write_text(
                redact(proc.stderr.read(16000)), encoding="utf-8")
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()

        self.addCleanup(cleanup)
        ready = json.loads(proc.stdout.readline())
        self.assertIn("port", ready, ready)

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        try:
            server = ThreadingHTTPServer(("127.0.0.1", 1420), partial(QuietHandler, directory=str(root / "desktop/dist")))
        except OSError:
            with urlopen("http://127.0.0.1:1420", timeout=3) as response:
                if "Local Agent Studio" not in response.read(10000).decode(errors="replace"):
                    self.skipTest("Port 1420 belongs to another application")
            # Reuse the existing frontend without stopping it; this test still
            # connects only to its isolated backend and database via the IPC bridge.
        else:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width":1440,"height":1000})
            # Only the native connection handshake is substituted. REST, SQLite,
            # uploads, WebSockets, worker processes and Ollama are real.
            page.add_init_script("window.__TAURI_INTERNALS__ = { invoke: async (cmd) => { "
                                 "if(cmd==='backend_connection'||cmd==='restart_backend') return " +
                                 json.dumps({"port":ready["port"],"token":token}) +
                                 "; throw new Error('Native command unavailable in browser acceptance'); } };")
            page.goto("http://127.0.0.1:1420")
            expect(page.locator(".local-status")).to_contain_text("Connected locally", timeout=15000)
            self.additional_ui_checks(page)
            page.locator('input[type="file"]').set_input_files({"name":"note.txt", "mimeType":"text/plain",
                                                               "buffer":b"The marker is ORCHID-UI-913."})
            expect(page.locator(".draft-attachments")).to_contain_text("note.txt")
            page.get_by_role("textbox", name="Message", exact=True).fill("Return only the exact marker in the attached note.")
            page.get_by_title("Send message", exact=True).click()
            expect(page.locator(".message.assistant .message-body").last).to_contain_text("ORCHID-UI-913", timeout=120000)
            page.locator(".message.user .attachment-chip").click()
            expect(page.get_by_role("dialog")).to_contain_text("ORCHID-UI-913")
            page.get_by_role("button", name="Close attachment preview").click()
            page.locator("textarea").evaluate("""element => {
                const canvas = document.createElement('canvas'); canvas.width=32; canvas.height=32;
                const context=canvas.getContext('2d');context.fillStyle='red';context.fillRect(0,0,32,32);
                const data=Uint8Array.from(atob(canvas.toDataURL('image/png').split(',')[1]), c=>c.charCodeAt(0));
                const transfer=new DataTransfer();transfer.items.add(new File([data],'clipboard.png',{type:'image/png'}));
                element.dispatchEvent(new ClipboardEvent('paste',{clipboardData:transfer,bubbles:true,cancelable:true}));
            }""")
            expect(page.locator(".draft-attachments")).to_contain_text("clipboard.png")
            page.get_by_title("Preview clipboard.png", exact=True).click()
            expect(page.get_by_role("dialog").locator("img")).to_be_visible()
            page.get_by_role("button", name="Close attachment preview").click()
            page.screenshot(path=str(root / "workspace/studio-attachments-acceptance.png"))
            page.get_by_title("Remove clipboard.png", exact=True).click()
            expect(page.locator(".draft-attachments")).to_have_count(0)
            page.locator(".composer").evaluate("""element => {
                const transfer=new DataTransfer();transfer.items.add(new File(['Dropped file content'],'dropped.txt',{type:'text/plain'}));
                element.dispatchEvent(new DragEvent('drop',{dataTransfer:transfer,bubbles:true,cancelable:true}));
            }""")
            expect(page.locator(".draft-attachments")).to_contain_text("dropped.txt")
            page.get_by_title("Remove dropped.txt", exact=True).click()
            with page.expect_download() as download:
                page.get_by_title("Export conversation as Markdown").click()
            self.assertTrue(download.value.suggested_filename.endswith(".md"))
            page.get_by_role("button", name="Capture screenshot", exact=True).click()
            expect(page.get_by_role("dialog")).to_contain_text("Capture your main screen?")
            page.get_by_role("button", name="Cancel", exact=True).click()
            page.locator(".chat-icon[title^='Rename']").first.click()
            page.get_by_role("dialog").get_by_role("textbox").fill("Attachment acceptance")
            page.get_by_role("button", name="Save name", exact=True).click()
            page.get_by_role("textbox", name="Search conversations").fill("Attachment acceptance")
            expect(page.locator(".conversation-row")).to_have_count(1)
            page.get_by_role("button", name="Delete Attachment acceptance", exact=True).click()
            expect(page.get_by_role("dialog")).to_contain_text("This cannot be undone")
            page.get_by_role("button", name="Delete conversation", exact=True).click()
            expect(page.locator(".conversation-row")).to_have_count(0)
            page.screenshot(path=str(root / "workspace/studio-features-acceptance.png"))
            browser.close()
