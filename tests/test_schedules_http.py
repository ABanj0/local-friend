"""Real authenticated runtime scheduling and rendered controls; model protocol fixture only."""
import json
import os
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import skipUnless
from urllib.error import HTTPError
from urllib.request import Request

from .inspection_support import InspectionModelFixture
from .studio_socket_support import HAS_SOCKET, StudioSocketFixture
from .support import WorkspaceTest


class ScheduleHTTPFixture(StudioSocketFixture, InspectionModelFixture):
    def start_backend(self):
        source = self.socket_config.read_text(encoding='utf-8')
        source = source.replace('url = "http://127.0.0.1:11434"', 'url = ' + json.dumps(self.config['model']['url']))
        self.socket_config.write_text(source, encoding='utf-8')
        super().start_backend()

    def post(self, path, data, *, token=None, origin='http://tauri.localhost'):
        request = Request(f'http://127.0.0.1:{self.port}{path}', data=json.dumps(data).encode(),
            headers={'Authorization': 'Bearer ' + (token or self.token), 'Origin': origin, 'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def body(self):
        return {'conversation': self.store.tasks()[0]['conversation'], 'objective': 'Inspect selected files',
            'model': self.config['model']['name'], 'project': '.', 'files': ['a.py', 'b.py'],
            'interval_ms': 60000, 'misfire': 'coalesce', 'timezone': 'America/Toronto'}

    def make_due(self, ident):
        with self.store.connection() as db:
            db.execute('UPDATE interval_schedules SET next_ms=? WHERE id=?', (time.time_ns() // 1_000_000 - 1, ident))


@skipUnless(HAS_SOCKET, 'Install desktop dependencies')
class ScheduleHTTPTests(ScheduleHTTPFixture, WorkspaceTest):
    def test_http_restart_misfire_runs_one_actual_inspection_and_disabled_work_never_runs(self):
        ident = self.post('/schedules', self.body())['id']
        self.stop_backend()
        self.make_due(ident)
        self.start_backend()
        self.wait_until(lambda: self.http('/schedules')['items'][0]['last'] is not None)
        self.wait_until(lambda: self.http('/schedules')['items'][0]['last']['task_status'] == 'reported')
        row = self.http('/schedules')['items'][0]
        self.assertEqual(row['id'], ident)
        task = row['last']['task']
        self.assertEqual({op['tool'] for op in self.http(f'/tasks/{task}/journal')['operations']}, {'read_file'})
        self.assertEqual(self.post(f'/schedules/{ident}/enabled', {'enabled': False}), {'enabled': False})
        self.stop_backend()
        self.make_due(ident)
        self.start_backend()
        time.sleep(.7)
        self.assertEqual(self.http('/schedules')['items'][0]['last']['task'], task)
        self.assertEqual(len(self.http('/tasks')['tasks']), 2)  # Includes the preexisting private fixture task.
        self.assertFalse(self.http('/schedules')['items'][0]['enabled'])

    def test_all_controls_require_auth_origin_strict_scope_and_explicit_resume(self):
        for token, origin, expected in [('x' * 64, 'http://tauri.localhost', 401),
                                         (self.token, 'http://untrusted.invalid', 403)]:
            for path, data in [('/schedules', self.body()), ('/scheduler/pause', {'paused': False, 'confirmed': True}),
                               ('/schedules/' + 'a' * 32 + '/enabled', {'enabled': True})]:
                with self.assertRaises(HTTPError) as failure:
                    self.post(path, data, token=token, origin=origin)
                self.assertEqual(failure.exception.code, expected)
        for change in ({'interval_ms': True}, {'interval_ms': 1000}, {'tool': 'command'}, {'timezone': 'Unknown/Zone'},
                       {'files': ['../outside']}, {'objective': self.token}):
            with self.assertRaises(HTTPError) as failure:
                self.post('/schedules', {**self.body(), **change})
            self.assertIn(failure.exception.code, (400, 403, 422))
        self.post('/emergency-stop', {})
        self.assertTrue(self.http('/schedules')['paused'])
        with self.assertRaises(HTTPError) as denied:
            self.post('/scheduler/pause', {'paused': False})
        self.assertEqual(denied.exception.code, 403)
        self.stop_backend()
        self.start_backend()
        self.assertTrue(self.http('/schedules')['paused'])
        self.post('/scheduler/pause', {'paused': False, 'confirmed': True})
        self.assertFalse(self.http('/schedules')['paused'])

    def test_emergency_stop_interrupts_actual_metadata_wait_and_persists_pause(self):
        self.metadata_gate.clear()
        ident = self.post('/schedules', self.body())['id']
        self.make_due(ident)
        self.assertTrue(self.metadata_entered.wait(8))
        started = time.monotonic()
        self.post('/emergency-stop', {})
        self.assertLess(time.monotonic() - started, 3)
        self.metadata_gate.set()
        self.assertTrue(self.http('/schedules')['paused'])
        self.assertTrue(self.http('/health')['ready'])
        self.assertEqual(len(self.http('/tasks')['tasks']), 1)
        self.stop_backend()
        self.assertIsNotNone(self.proc.returncode)


@skipUnless(os.getenv('LIVE_STUDIO_UI') == '1', 'Rendered interval UI is opt-in after frontend build')
class ScheduleUITests(ScheduleHTTPFixture, WorkspaceTest):
    def test_schedule_controls_actual_runtime_task_stop_and_disable_at_900px(self):
        from playwright.sync_api import expect, sync_playwright

        root = Path.cwd()
        server = ThreadingHTTPServer(('127.0.0.1', 1420), partial(SimpleHTTPRequestHandler, directory=str(root / 'desktop/dist')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 900, 'height': 1050})
            page.add_init_script('window.__TAURI_INTERNALS__={invoke:async()=>(' +
                                 json.dumps({'port': self.port, 'token': self.token}) + ')};')
            page.goto('http://127.0.0.1:1420')
            expect(page.locator('.local-status')).to_contain_text('Connected locally', timeout=15000)
            page.get_by_role('button', name='Workspace', exact=True).click()
            panel = page.get_by_role('region', name='Scheduled read-only inspections')
            panel.locator('summary').click()
            panel.get_by_role('textbox', name='Schedule files', exact=True).fill('a.py\nb.py')
            panel.get_by_role('textbox', name='Schedule question', exact=True).fill('Inspect selected files')
            panel.get_by_role('spinbutton', name='Schedule interval in minutes').fill('1')
            panel.get_by_role('combobox', name='Schedule timezone').select_option('America/Toronto')
            panel.get_by_role('button', name='Enable interval inspection', exact=True).click()
            expect(panel.get_by_role('button', name='Disable interval inspection')).to_be_enabled()
            row = self.http('/schedules')['items'][0]
            ident = row['id']
            self.assertEqual(row['timezone'], 'America/Toronto')
            self.make_due(ident)
            expect(panel).to_contain_text('task reported', timeout=20000)
            panel.get_by_role('button', name='Open latest inspection task').click()
            expect(page.get_by_role('region', name='Resumable repository inspection')).to_contain_text('Selected inspection')
            panel.get_by_role('button', name='Disable interval inspection').click()
            expect(panel).to_contain_text('Disabled')
            page.get_by_role('button', name='Emergency stop', exact=True).first.click()
            expect(panel).to_contain_text('Automatic inspections are paused', timeout=10000)
            panel.get_by_role('button', name='Resume scheduled inspections').click()
            expect(panel.get_by_role('button', name='Pause scheduled inspections')).to_be_enabled()
            self.assertFalse(self.http('/schedules')['paused'])
            self.assertFalse(self.http('/schedules')['items'][0]['enabled'])
            completed = self.http('/schedules')['items'][0]['last']['task']
            self.assertEqual({op['tool'] for op in self.http(f'/tasks/{completed}/journal')['operations']}, {'read_file'})
            panel.get_by_role('button', name='Enable saved inspection').scroll_into_view_if_needed()
            page.screenshot(path=str(root / '.runtime/p2-03-interval/schedules-900px.png'))
            browser.close()
