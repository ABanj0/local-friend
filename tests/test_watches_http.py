"""Real watch API/runtime/UI with explicit model protocol and native IPC fixtures."""
import os
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import skipUnless
from urllib.error import HTTPError

from .studio_socket_support import HAS_SOCKET
from .support import WorkspaceTest
from .test_schedules_http import ScheduleHTTPFixture


class WatchHTTPFixture(ScheduleHTTPFixture):
    def watch_body(self):
        return {key: value for key, value in self.body().items() if key not in {'interval_ms', 'misfire', 'timezone'}} | {
            'directory': '.', 'debounce_ms': 1000}

    def watch(self):
        return self.http('/watches')['items'][0]

    def due(self, *, mature=False):
        with self.store.connection() as db:
            db.execute('UPDATE directory_watches SET next_ms=0')
            if mature:
                db.execute('UPDATE directory_watches SET candidate_ms=candidate_ms-1000')

    def changed(self):
        (self.policy.root / 'a.py').write_text('def add(a,b):\n    return a+b+0\n', encoding='utf-8')
        self.due()


@skipUnless(HAS_SOCKET, 'Install desktop dependencies')
class WatchHTTPTests(WatchHTTPFixture, WorkspaceTest):
    def test_real_debounce_restart_one_worker_and_disabled_changes_create_no_more_tasks(self):
        ident = self.post('/watches', self.watch_body())['id']
        self.wait_until(lambda: self.watch()['status'] == 'ready')
        self.assertEqual(self.requests, [])
        self.changed()
        self.wait_until(lambda: self.watch()['status'] == 'debouncing')
        self.stop_backend()
        self.due(mature=True)
        self.start_backend()
        self.wait_until(lambda: self.watch()['last'] is not None)
        self.wait_until(lambda: self.watch()['last']['task_status'] == 'reported')
        first = self.watch()
        self.assertEqual(first['generation'], 1)
        self.assertEqual({op['tool'] for op in self.http(f"/tasks/{first['last']['task']}/journal")['operations']}, {'read_file'})
        self.post(f'/watches/{ident}/enabled', {'enabled': False})
        self.stop_backend()
        self.changed()
        self.start_backend()
        time.sleep(.7)
        self.assertEqual(self.watch()['generation'], 1)
        self.assertEqual(self.watch()['last'], first['last'])
        self.assertEqual(len(self.http('/tasks')['tasks']), 2)

    def test_auth_origin_strict_scope_and_global_stop_resume_cannot_be_bypassed(self):
        for path, data in [('/watches', self.watch_body()), ('/watches/' + 'a' * 32 + '/enabled', {'enabled': False})]:
            for token, origin, code in [('x' * 64, 'http://tauri.localhost', 401), (self.token, 'http://untrusted.invalid', 403)]:
                with self.assertRaises(HTTPError) as error:
                    self.post(path, data, token=token, origin=origin)
                self.assertEqual(error.exception.code, code)
        for change in ({'directory': '../outside'}, {'directory': '.git'}, {'directory': 'x' * 241},
                       {'debounce_ms': True}, {'command': 'test'}, {'files': ['.env']}, {'objective': self.token}):
            with self.subTest(change=change), self.assertRaises(HTTPError) as error:
                self.post('/watches', {**self.watch_body(), **change})
            self.assertIn(error.exception.code, (400, 403, 422))
        self.post('/watches', self.watch_body())
        self.wait_until(lambda: self.watch()['status'] == 'ready')
        self.post('/emergency-stop', {})
        self.changed()
        time.sleep(.6)
        self.assertTrue(self.http('/watches')['paused'])
        self.assertIsNone(self.watch()['last'])
        with self.assertRaises(HTTPError) as denied:
            self.post('/scheduler/pause', {'paused': False})
        self.assertEqual(denied.exception.code, 403)
        self.assertEqual(self.requests, [])

    def test_incomplete_scan_is_not_a_baseline_or_task_and_restore_invalidates_old_authority(self):
        oversized = self.policy.root / 'large.bin'
        oversized.write_bytes(b'x' * 64001)
        self.post('/watches', self.watch_body())
        self.wait_until(lambda: self.watch()['status'] == 'incomplete')
        self.assertIsNone(self.watch()['last'])
        oversized.unlink()
        self.due()
        self.wait_until(lambda: self.watch()['status'] == 'ready')
        saved = self.post('/backups', {'confirmed': True})
        draft = self.post('/restore/prepare', {'backup': saved['id'], 'sha256': saved['sha256'], 'confirmed': True})
        self.post('/restore/activate', {'preparation': draft['id'], 'sha256': draft['database_sha256'], 'confirmed': True})
        self.stop_backend()
        self.start_backend()
        self.wait_until(lambda: not self.watch()['enabled'])
        self.assertEqual(self.watch()['status'], 'input_changed')
        self.assertEqual(self.requests, [])
        self.assertIsNone(self.watch()['last'])


@skipUnless(os.getenv('LIVE_STUDIO_UI') == '1', 'Rendered directory workflow is opt-in after frontend build')
class WatchUITests(WatchHTTPFixture, WorkspaceTest):
    def test_real_directory_change_inspection_stop_disable_and_task_open_at_900px(self):
        import json

        from playwright.sync_api import expect, sync_playwright

        root = Path.cwd()
        server = ThreadingHTTPServer(('127.0.0.1', 1420), partial(SimpleHTTPRequestHandler, directory=str(root / 'desktop/dist')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 900, 'height': 1050})
            page.add_init_script('window.__TAURI_INTERNALS__={invoke:async()=>(' + json.dumps({'port': self.port, 'token': self.token}) + ')};')
            page.goto('http://127.0.0.1:1420')
            expect(page.locator('.local-status')).to_contain_text('Connected locally', timeout=15000)
            page.get_by_role('button', name='Workspace', exact=True).click()
            panel = page.get_by_role('region', name='Directory-triggered inspections')
            panel.locator('summary').click()
            panel.get_by_role('textbox', name='Watch inspection files').fill('a.py\nb.py')
            panel.get_by_role('spinbutton', name='Directory debounce seconds').fill('1')
            panel.get_by_role('button', name='Enable directory inspection', exact=True).click()
            expect(panel).to_contain_text('Enabled · ready', timeout=15000)
            self.assertEqual(self.requests, [])
            self.changed()
            self.wait_until(lambda: self.watch()['status'] == 'debouncing')
            self.due(mature=True)
            expect(panel).to_contain_text('task reported', timeout=20000)
            panel.get_by_role('button', name='Open directory inspection task').click()
            expect(page.get_by_role('region', name='Resumable repository inspection')).to_contain_text('Selected inspection')
            panel.get_by_role('button', name='Disable directory inspection').click()
            expect(panel).to_contain_text('Disabled · disabled')
            page.get_by_role('button', name='Emergency stop', exact=True).first.click()
            expect(panel.get_by_role('button', name='Resume automatic inspections')).to_be_enabled()
            panel.get_by_role('button', name='Resume automatic inspections').click()
            expect(panel.get_by_role('button', name='Pause automatic inspections')).to_be_enabled()
            self.assertFalse(self.watch()['enabled'])
            self.assertEqual(self.watch()['generation'], 1)
            panel.get_by_role('button', name='Enable saved directory inspection').scroll_into_view_if_needed()
            page.screenshot(path=str(root / '.runtime/p2-03-directory-workflow/watch-900px.png'))
            browser.close()
