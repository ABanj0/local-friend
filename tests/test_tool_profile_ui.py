"""Actual frontend/backend/approved execution; inference is an explicit protocol fixture."""
import hashlib
import json
import os
import re
import sys
import threading
import time
import unittest
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from .fixture_site import FixtureSite
from .ollama_fixture import serve_metadata
from .studio_socket_support import StudioSocketFixture
from .support import WorkspaceTest
from .test_background import free_port, server_source


@unittest.skipUnless(os.getenv("LIVE_STUDIO_UI") == "1", "Rendered tool-profile acceptance is opt-in")
class ToolProfileUITests(StudioSocketFixture, WorkspaceTest):
    def start_backend(self):
        self.inference_requests = []
        requests = self.inference_requests
        model_name = self.config["model"]["name"]
        background_case = self._testMethodName.startswith("test_background_")
        scoped_case = self._testMethodName.startswith("test_scoped_")
        accessibility_case = self._testMethodName.startswith("test_keyboard_")
        message_case = self._testMethodName.startswith("test_message_pages_")
        task_case = self._testMethodName.startswith("test_task_history_pages_")
        inspection_case = self._testMethodName.startswith('test_inspection_')
        semantic_case = self._testMethodName.startswith('test_semantic_')
        embedding_name = 'fixture-embedding'
        self.embedding_requests = []
        embedding_requests = self.embedding_requests
        self.embedding_gate, self.embedding_entered = threading.Event(), threading.Event()
        self.embedding_gate.set()
        self.addCleanup(self.embedding_gate.set)
        embedding_gate, embedding_entered = self.embedding_gate, self.embedding_entered
        self.scoped_site = self.enterContext(FixtureSite()) if scoped_case else None
        scoped_url = self.scoped_site.url if self.scoped_site else None
        self.inspection_gate = threading.Event()
        inspection_gate = self.inspection_gate
        self.addCleanup(inspection_gate.set)
        self.scoped_plan_gate = threading.Event()
        self.scoped_plan_gate.set()
        scoped_gate = self.scoped_plan_gate
        if background_case:
            self.background_port = free_port()

        class Metadata(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if semantic_case and self.path == '/api/tags':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(json.dumps({'models': [{'name': name, 'digest': ('b' if name == embedding_name else 'a') * 64,
                        'details': {'format': 'gguf'}} for name in (model_name, embedding_name)]}).encode())
                    return
                if serve_metadata(self, name=model_name):
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"models": [{"name": model_name}]}).encode())

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if semantic_case and (self.path == '/api/embed' or self.path == '/api/show' and body.get('model') == embedding_name):
                    if self.path == '/api/embed':
                        embedding_requests.append(body)
                        embedding_entered.set()
                        embedding_gate.wait(15)
                        response = {'model': embedding_name, 'embeddings': [[1., 0.] for _ in body['input']],
                                    'total_duration': 1000, 'load_duration': 100, 'prompt_eval_count': 5}
                    else:
                        response = {'capabilities': ['embedding'], 'details': {'format': 'gguf'},
                                    'model_info': {'fixture.embedding_length': 2}}
                    self.send_response(200)
                    self.end_headers()
                    try:
                        self.wfile.write(json.dumps(response).encode())
                    except ConnectionError:
                        pass  # Emergency stop closes only this owned fixture request.
                    return
                if serve_metadata(self, body, name=model_name):
                    return
                requests.append(body)
                if semantic_case and body.get('stream'):
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(json.dumps({'message': {'role': 'assistant', 'content': 'Semantic fixture reply.'},
                        'done': True, 'done_reason': 'stop', 'eval_count': 5, 'eval_duration': 100000000}).encode())
                    return
                objective = next((message.get("content", "") for message in reversed(body["messages"])
                                  if message["role"] == "user" and message.get("content", "").startswith(
                                      ("Capture scoped browser preview", "Create second scoped artifact"))), "")
                if inspection_case and not body.get('format'):
                    observed = [message for message in body['messages'] if message['role'] == 'tool']
                    if len(observed) >= 2:
                        message = {'content': 'Selected files inspected. No mutations or commands were executed.'}
                    else:
                        if len(observed) == 1:
                            inspection_gate.wait(30)
                        message = {'tool_calls': [{'function': {'name': 'read_file', 'arguments': {
                            'path': 'a.py' if not observed else 'b.py'}}}]}
                elif body.get("format"):
                    if accessibility_case or message_case or task_case or (scoped_case and objective.startswith("Create second scoped artifact")):
                        scoped_gate.wait(15)
                    message = {"content": '{"steps":["Create the reviewed artifact"]}'}
                elif scoped_case and objective.startswith("Capture scoped browser preview"):
                    used = [m.get("tool_name") for m in body["messages"] if m["role"] == "tool"]
                    if "browser_open" not in used:
                        message = {"tool_calls": [{"function": {"name": "browser_open", "arguments": {
                            "url": scoped_url}}}]}
                    elif "browser_screenshot" not in used:
                        message = {"tool_calls": [{"function": {"name": "browser_screenshot", "arguments": {}}}]}
                    else:
                        message = {"content": "SCOPED-A-RESULT: browser preview observed."}
                elif any(message["role"] == "tool" for message in body["messages"]):
                    used = [m.get("tool_name") for m in body["messages"] if m["role"] == "tool"]
                    if background_case and "command" not in used:
                        name = "command" if "command_status" in used else "command_status"
                        message = {"tool_calls": [{"function": {"name": name,
                            "arguments": {"name": "test" if name == "command" else "ui_background"}}}]}
                    elif scoped_case and "write_file" in used and "command" not in used:
                        message = {"tool_calls": [{"function": {"name": "command", "arguments": {"name": "test"}}}]}
                    else:
                        message = {"content": "Fixture write completed; inspect the readback evidence."}
                elif background_case:
                    message = {"tool_calls": [{"function": {"name": "start_command",
                        "arguments": {"name": "ui_background"}}}]}
                elif any(m.get("content") == "Apply reviewed patch set" for m in body["messages"]):
                    message = {"tool_calls": [{"function": {"name": "apply_patch", "arguments": {"changes": [
                        {"path": "sample.txt", "expected_sha256": hashlib.sha256(b"profile acceptance").hexdigest(),
                         "text": "reviewed patch"},
                        {"path": "related.txt", "expected_sha256": "missing", "text": "related patch"}]}}}]}
                else:
                    message = {"tool_calls": [{"function": {"name": "write_file", "arguments": {
                        "path": "stopped-artifact.txt" if accessibility_case and any(
                            m.get("content") == "Stop before new artifact" for m in body["messages"])
                            else "artifact.txt", "text": "reviewed fixture"}}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"message": {"role": "assistant", **message}, "done": True, "done_reason": "stop",
                    "eval_count": 10, "eval_duration": 1_000_000_000, "prompt_eval_count": 12,
                    "load_duration": 20_000_000, "prompt_eval_duration": 30_000_000}).encode())

        model = ThreadingHTTPServer(("127.0.0.1", 0), Metadata)
        threading.Thread(target=model.serve_forever, daemon=True).start()
        self.addCleanup(model.server_close)
        self.addCleanup(model.shutdown)
        source = self.socket_config.read_text(encoding="utf-8")
        if scoped_case:
            source = source.replace('allowed_origins = [', 'allowed_origins = [' + json.dumps(scoped_url) + ',')
            source = source.replace('[browser]', '[browser]\nchannel = "msedge"')
        if background_case:
            source = source.replace("[commands]", '[commands]\nui_background = ["{python}", "ui-background.py"]')
            source += f'\n[readiness.ui_background]\nurl = "http://127.0.0.1:{self.background_port}/health"\ntimeout = 5\n'
        if "[runtime]" not in source:
            source += "\n[runtime]\npython = " + json.dumps(sys.executable) + "\n"
        self.socket_config.write_text(source.replace("127.0.0.1:11434", f"127.0.0.1:{model.server_port}"),
                                      encoding="utf-8")
        super().start_backend()

    def test_profile_selection_denial_then_approved_tests(self):
        self.run_profile_scenario()

    def test_reviewed_write_displays_artifact_evidence(self):
        self.run_profile_scenario(artifact=True)

    def test_run_diagnostics_export_excludes_content_and_retains_verifier_links(self):
        self.run_profile_scenario(artifact=True, diagnostics=True)

    def test_journal_inspects_current_files_and_opens_instruction_without_replay(self):
        self.run_profile_scenario(artifact=True, journal=True)

    def test_restored_unknown_journal_is_visible_and_inspection_keeps_outcome_unknown(self):
        self.run_profile_scenario(artifact=True, journal="unknown")

    def test_inference_settings_persist_reach_agent_and_display_native_timing(self):
        self.run_profile_scenario(artifact=True, inference=True)

    def test_context_compaction_notice_is_visible_and_scoped_to_selected_conversation(self):
        self.run_profile_scenario(artifact=True, context_case=True)

    def test_context_reserve_blocks_generation_and_explains_how_to_fit(self):
        self.run_profile_scenario(artifact=True, context_blocked=True)

    def test_scoped_activity_preview_and_global_approval_survive_conversation_switching(self):
        self.run_profile_scenario(scoped_case=True)

    def test_keyboard_dialogs_and_activity_drawer_at_900px(self):
        self.run_profile_scenario(accessibility=True)

    def test_conversation_pages_search_pin_selected_and_ignore_stale_results(self):
        self.run_profile_scenario(conversation_case=True)

    def test_message_pages_live_updates_scope_and_complete_export(self):
        self.run_profile_scenario(message_case=True)

    def test_task_history_pages_keep_selection_and_global_owned_actions(self):
        self.run_profile_scenario(task_case=True)

    def test_confirmed_backup_preserves_data_and_refuses_owned_worker(self):
        self.run_profile_scenario(backup_case=True)

    def test_retention_preview_confirmation_stale_review_and_selected_chat_preservation(self):
        self.run_profile_scenario(retention_case=True)

    def test_inspection_pauses_restarts_resumes_and_preserves_read_only_scope(self):
        self.run_profile_scenario(restore_case=True, inspection_case=True)

    def test_restore_and_rollback_restart_actual_backend_and_reset_selected_context(self):
        self.run_profile_scenario(restore_case=True)

    def test_memory_saves_source_searches_and_confirms_forget_and_chat_cascade(self):
        self.run_profile_scenario(memory_case=True)

    def test_memory_slash_commands_confirm_forget_and_do_not_reopen_on_navigation(self):
        self.run_profile_scenario(memory_case="slash")

    def test_workspace_search_opens_real_file_and_reports_limits(self):
        self.run_profile_scenario(search=True)

    def test_semantic_note_index_confirmation_recall_stop_and_stale_scope(self):
        self.run_profile_scenario(semantic_case=True)

    def test_saved_file_provenance_stale_listing_and_confirmed_whole_source_forget(self):
        self.run_profile_scenario(memory_file_case=True)

    def test_file_source_review_import_conflict_reimport_and_forget(self):
        self.run_profile_scenario(memory_file_case='review')

    def test_file_source_late_preview_and_listing_cannot_cross_project_navigation(self):
        self.run_profile_scenario(memory_file_case='navigation')

    def test_file_source_blank_conversation_and_late_metadata_are_scoped(self):
        self.run_profile_scenario(memory_file_case='empty')

    def run_file_empty_conversation_scenario(self, page):
        from playwright.sync_api import expect

        path = self.policy.root / 'blank-chat.txt'
        path.write_text('Explicit file memory without an existing selected conversation.\n', encoding='utf-8')
        page.set_viewport_size({'width': 900, 'height': 900})
        page.get_by_role('button', name='Project memory', exact=True).click()
        controls = page.get_by_role('region', name='Saved file sources', exact=True)
        controls.get_by_role('textbox', name='Project-relative source file').fill(path.name)
        controls.get_by_role('button', name='Preview file', exact=True).click()
        dialog = page.get_by_role('dialog', name='Save this file as memory?', exact=True)
        expect(dialog.get_by_role('button', name='Cancel', exact=True)).to_be_focused()
        self.assertTrue(dialog.evaluate('(d)=>d.scrollWidth<=d.clientWidth'))
        dialog.get_by_role('button', name='Save file memory', exact=True).click()
        expect(controls.locator('li')).to_have_count(1)
        expect(page.locator('.memory-page article')).to_have_count(1)
        source = self.http('/memory/sources')[0]
        self.assertNotEqual(source['conversation'], self.store.tasks()[0]['conversation'])
        self.assertEqual(self.store.conversation_metadata(source['conversation'])['title'], 'Project memory')
        self.assertFalse(self.inference_requests)

        held = []

        def delay_listing(route):
            held.append((route, route.fetch()))
            page.evaluate('window.__heldSourceMetadata=(window.__heldSourceMetadata||0)+1')

        page.route('**/memory/sources?project=.', delay_listing)
        page.get_by_role('button', name='Chat', exact=True).click()
        page.get_by_role('navigation', name='Workspaces').get_by_role('button', name='Project memory', exact=True).click()
        page.wait_for_function('window.__heldSourceMetadata>0')
        (self.policy.root / 'other').mkdir()
        chosen = str(self.policy.root / 'other')
        page.evaluate('(chosen)=>{const previous=window.__TAURI_INTERNALS__.invoke;'
            'window.__TAURI_INTERNALS__.invoke=async(name,args)=>name==="plugin:dialog|open"?chosen:previous(name,args);}', chosen)
        page.get_by_role('button', name='Choose project', exact=True).click()
        expect(page.locator('.memory-page .page-intro code')).to_have_text('other')
        for route, response in held:
            self.assertEqual(response.json()[0]['path'], path.name)
            route.fulfill(response=response)
        page.unroute('**/memory/sources?project=.', delay_listing)
        expect(controls).to_contain_text('No saved file sources')
        expect(controls).not_to_contain_text(path.name)
        expect(page.locator('.memory-page article')).to_have_count(0)
        self.assertEqual(path.read_text(encoding='utf-8'), 'Explicit file memory without an existing selected conversation.\n')

    def run_file_review_scenario(self, page, navigation=False):
        from playwright.sync_api import expect

        path = self.policy.root / 'guide.txt'
        original = b'\xef\xbb\xbf' + b'Lavender release historical note.\r\n' * 36
        path.write_bytes(original)
        mutations = []
        page.on('request', lambda req: mutations.append(req.post_data_json)
                if req.method == 'POST' and req.url.endswith('/memory/sources') else None)
        page.get_by_role('button', name='WEBSOCKET-PRIVATE-CANARY', exact=True).click()
        page.get_by_role('button', name='Project memory', exact=True).click()
        controls = page.get_by_role('region', name='Saved file sources', exact=True)
        field = controls.get_by_role('textbox', name='Project-relative source file', exact=True)
        field.fill('guide.txt')

        if navigation:
            held = []

            def delay_preview(route):
                held.append((route, route.fetch()))

            page.route('**/memory/sources/preview', delay_preview)
            controls.get_by_role('button', name='Preview file', exact=True).click()
            expect(controls.get_by_role('status')).to_contain_text('Working')
            page.wait_for_function('document.querySelector(".file-memory button").disabled')
            # Navigation remains available while the response is delayed; another project
            # must never receive the old preview or its authority to import.
            (self.policy.root / 'other').mkdir()
            chosen = str(self.policy.root / 'other')
            page.get_by_role('button', name='Chat', exact=True).click()
            page.get_by_role('button', name='Project memory', exact=True).click()
            page.evaluate('(chosen)=>{const previous=window.__TAURI_INTERNALS__.invoke;'
                'window.__TAURI_INTERNALS__.invoke=async(name,args)=>name==="plugin:dialog|open"?chosen:previous(name,args);}', chosen)
            page.get_by_role('button', name='Choose project', exact=True).click()
            expect(field).to_have_value('')
            self.assertEqual(len(held), 1)
            for route, response in held:
                route.fulfill(response=response)
            page.unroute('**/memory/sources/preview', delay_preview)
            expect(page.get_by_role('dialog')).to_have_count(0)
            expect(controls).to_contain_text('No saved file sources')
            expect(controls).not_to_contain_text('guide.txt')
            self.assertFalse(mutations)
            self.assertFalse(self.http('/memory/sources'))
            self.assertEqual(path.read_bytes(), original)
            return

        preview_button = controls.get_by_role('button', name='Preview file', exact=True)
        preview_button.click()
        dialog = page.get_by_role('dialog', name='Save this file as memory?', exact=True)
        expect(dialog).to_contain_text(hashlib.sha256(original).hexdigest())
        expect(dialog).to_contain_text('lines 1')
        expect(dialog).to_contain_text('utf8-bom-newlines-v1')
        expect(dialog.locator('.file-excerpts')).to_contain_text('Lavender')
        self.assertFalse(self.http('/memory/sources'))
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        self.assertFalse(mutations)
        preview_button.click()
        dialog.get_by_role('button', name='Save file memory', exact=True).click()
        expect(dialog).to_have_count(0)
        expect(controls.locator('li')).to_have_count(1)
        saved = self.http('/memory/sources')[0]
        excerpts = self.http('/memory')
        self.assertGreater(len(excerpts), 1)
        expect(page.locator('.memory-page article')).to_have_count(len(excerpts))
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(mutations), 1)
        self.assertTrue(mutations[0]['confirmed'])
        self.assertIsNone(mutations[0]['expected_generation'])

        path.write_text('Beta revised source\n', encoding='utf-8', newline='')
        controls.get_by_role('button', name='Check sources', exact=True).click()
        expect(controls.locator('li')).to_contain_text('stale')
        controls.get_by_role('button', name='Review reimport', exact=True).click()
        replacement = page.get_by_role('dialog', name='Replace saved file excerpts?', exact=True)
        expect(replacement).to_contain_text('Beta revised source')
        replacement.get_by_role('button', name='Cancel', exact=True).click()
        self.assertEqual(self.http('/memory/sources')[0]['generation'], saved['generation'])
        controls.get_by_role('button', name='Review reimport', exact=True).click()
        expect(replacement).to_be_visible()
        path.write_text('Gamma final source\n', encoding='utf-8', newline='')
        replacement.get_by_role('button', name='Replace saved excerpts', exact=True).click()
        expect(controls.get_by_role('alert')).to_contain_text('Source changed since preview')
        self.assertEqual(self.http('/memory/sources')[0]['generation'], saved['generation'])
        controls.get_by_role('button', name='Review reimport', exact=True).click()
        expect(replacement).to_contain_text('Gamma final source')
        replacement.get_by_role('button', name='Replace saved excerpts', exact=True).click()
        expect(controls.locator('li')).to_contain_text('current')
        expect(page.locator('.memory-page article')).to_have_count(1)
        expect(page.locator('.memory-page article')).to_contain_text('Gamma final source')
        self.assertNotEqual(self.http('/memory/sources')[0]['generation'], saved['generation'])
        self.assertEqual(mutations[-1]['expected_generation'], saved['generation'])
        field.fill('../outside.txt')
        preview_button.click()
        expect(controls.get_by_role('alert')).to_be_visible()
        expect(page.get_by_role('dialog')).to_have_count(0)
        self.assertEqual(len(self.http('/memory/sources')), 1)
        self.assertFalse(self.inference_requests)
        self.assertFalse(self.embedding_requests)
        controls.get_by_role('button', name='Forget saved file', exact=True).click()
        forgetting = page.get_by_role('dialog', name='Forget saved file source?', exact=True)
        expect(forgetting).to_contain_text('original file stays unchanged')
        forgetting.get_by_role('button', name='Cancel', exact=True).click()
        self.assertEqual(len(self.http('/memory/sources')), 1)
        controls.get_by_role('button', name='Forget saved file', exact=True).click()
        forgetting.get_by_role('button', name='Forget all excerpts', exact=True).click()
        expect(controls.locator('li')).to_have_count(0)
        expect(page.locator('.memory-page article')).to_have_count(0)
        self.assertEqual(self.http('/memory/sources'), [])
        self.assertEqual(path.read_bytes(), b'Gamma final source\n')

    def run_memory_file_scenario(self, page):
        from playwright.sync_api import expect
        path = self.policy.root / 'guide.txt'
        path.write_text('Historical file fact: lavender release.\n' * 40, encoding='utf-8', newline='')
        original = path.read_bytes()
        chat = self.store.tasks()[0]['conversation']

        def post(route, body):
            response = page.request.post(f'http://127.0.0.1:{self.port}{route}',
                headers={'Authorization': 'Bearer ' + self.token}, data=body)
            self.assertEqual(response.status, 200, response.text())
            return response.json()

        preview = post('/memory/sources/preview', {'path': path.name})
        body = {k: preview[k] for k in ('path', 'sha256', 'version', 'expected_generation')}
        imported = post('/memory/sources', {**body, 'conversation': chat, 'confirmed': True})
        self.assertGreater(imported['chunks'], 1)
        page.get_by_role('button', name='WEBSOCKET-PRIVATE-CANARY', exact=True).click()
        page.get_by_role('button', name='Project memory', exact=True).click()
        articles = page.locator('.memory-page article')
        expect(articles).to_have_count(imported['chunks'])
        expect(articles.first).to_contain_text('Saved file excerpt')
        expect(articles.first).to_contain_text('guide.txt')
        expect(articles.first).to_contain_text('lines')
        path.write_text('Updated source file content\n', encoding='utf-8', newline='')
        page.get_by_role('textbox', name='Search project memory').fill('lavender')
        page.get_by_role('button', name='Search', exact=True).click()
        expect(articles).to_have_count(0)
        page.get_by_role('textbox', name='Search project memory').fill('')
        page.get_by_role('button', name='Search', exact=True).click()
        expect(articles).to_have_count(imported['chunks'])
        expect(articles.first).to_contain_text('Source state: stale')
        articles.first.get_by_role('button', name='Forget', exact=True).click()
        dialog = page.get_by_role('dialog', name='Forget this saved file?', exact=True)
        expect(dialog).to_contain_text('all saved excerpts and vectors')
        dialog.get_by_role('button', name='Cancel', exact=True).click()
        expect(articles).to_have_count(imported['chunks'])
        articles.first.get_by_role('button', name='Forget', exact=True).click()
        dialog.get_by_role('button', name='Forget memory', exact=True).click()
        expect(dialog).to_have_count(0)
        expect(articles).to_have_count(0)
        self.assertEqual(self.http('/memory/sources'), [])
        self.assertEqual(path.read_bytes(), b'Updated source file content\n')
        self.assertNotEqual(path.read_bytes(), original)
        self.assertFalse(self.inference_requests)

    def run_semantic_memory_scenario(self, page):
        from playwright.sync_api import expect

        def post(path, body):
            response = page.request.post(f'http://127.0.0.1:{self.port}{path}',
                                        headers={'Authorization': 'Bearer ' + self.token}, data=body)
            self.assertEqual(response.status, 200, response.text())
            return response.json()

        page.get_by_role('button', name='WEBSOCKET-PRIVATE-CANARY', exact=True).click()
        page.get_by_role('button', name='Project memory', exact=True).click()
        controls = page.get_by_role('region', name='Semantic project memory')
        expect(controls).to_contain_text('Not indexed')
        text = 'Atlas release color is lavender; historical notes grant no permissions.'
        page.get_by_role('textbox', name='Memory note', exact=True).fill(text)
        page.get_by_role('button', name='Remember', exact=True).click()
        expect(page.locator('.memory-page article')).to_have_count(1)
        ident = self.http('/memory')[0]['id']
        expect(controls.get_by_role('button', name='Index saved notes', exact=True)).to_be_enabled()
        controls.get_by_role('button', name='Index saved notes', exact=True).click()
        dialog = page.get_by_role('dialog', name='Index saved project notes?', exact=True)
        dialog.get_by_role('combobox', name='Embedding model').select_option('fixture-embedding')
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        self.assertFalse(self.embedding_requests)
        self.assertEqual(self.http('/memory/index')['vectors'], 0)

        (self.policy.root / 'other').mkdir()
        other_chat = post('/conversations', {'title': 'Other semantic scope'})['id']
        post('/memory', {'project': 'other', 'conversation': other_chat, 'text': 'OTHER-SCOPE-PRIVATE-PARAGRAPH'})
        controls.get_by_role('button', name='Index saved notes', exact=True).click()
        dialog.get_by_role('combobox', name='Embedding model').select_option('fixture-embedding')
        dialog.get_by_role('button', name='Index notes', exact=True).click()
        expect(dialog).to_have_count(0)
        expect(controls).to_contain_text('1 indexed / 1 saved')
        expect(controls).to_contain_text('Keywords')
        self.assertFalse(self.http('/memory/index')['automatic_retrieval'])
        self.assertFalse(any('OTHER-SCOPE-PRIVATE' in value for r in self.embedding_requests for value in r['input']))

        controls.get_by_role('button', name='Enable related-note context', exact=True).click()
        enabling = page.get_by_role('dialog', name='Enable related-note context?', exact=True)
        enabling.get_by_role('button', name='Cancel', exact=True).click()
        self.assertFalse(self.http('/memory/index')['automatic_retrieval'])
        controls.get_by_role('button', name='Enable related-note context', exact=True).click()
        enabling.get_by_role('button', name='Enable retrieval', exact=True).click()
        expect(enabling).to_have_count(0)
        expect(controls).to_contain_text('Related wording')
        self.assertTrue(self.http('/memory/index')['automatic_retrieval'])
        page.get_by_role('combobox', name='Memory search mode', exact=True).select_option('semantic')
        page.get_by_role('textbox', name='Search project memory').fill('Which deployment hue?')
        page.get_by_role('button', name='Search', exact=True).click()
        expect(page.get_by_role('button', name='Search', exact=True)).to_be_enabled()
        expect(page.locator('.memory-page article')).to_contain_text(text)
        self.assertTrue(self.embedding_requests[-1]['input'][0].endswith('Which deployment hue?'))

        page.get_by_role('button', name='Chat', exact=True).click()
        composer = page.get_by_role('textbox', name='Message', exact=True)
        composer.fill('Which deployment hue?')
        page.get_by_title('Send message', exact=True).click()
        expect(page.locator('.message.assistant').last).to_contain_text('Semantic fixture reply.', timeout=15000)
        expect(page.locator('.message.assistant').last).to_contain_text('memory:' + ident)
        self.assertIn('UNTRUSTED HISTORICAL MEMORY', self.inference_requests[-1]['messages'][-1]['content'])
        self.assertIn(text, self.inference_requests[-1]['messages'][-1]['content'])
        self.assertNotIn('tools', self.inference_requests[-1])

        page.get_by_role('button', name='Project memory', exact=True).click()
        expect(controls).to_contain_text('Related wording')
        controls.get_by_role('button', name='Use keyword context', exact=True).click()
        expect(controls).to_contain_text('Keywords')
        self.assertFalse(self.http('/memory/index')['automatic_retrieval'])

        # A pending confirmed reindex leaves the global emergency-stop control usable.
        with self.store.connection() as db:
            generation = db.execute('SELECT generation FROM memory_indexes').fetchone()[0]
        self.embedding_entered.clear()
        self.embedding_gate.clear()
        try:
            controls.get_by_role('button', name='Index saved notes', exact=True).click()
            dialog.get_by_role('combobox', name='Embedding model').select_option('fixture-embedding')
            dialog.get_by_role('button', name='Index notes', exact=True).click()
            expect(dialog).to_have_count(0)
            self.assertTrue(self.embedding_entered.wait(3))
            page.get_by_role('button', name='Emergency stop', exact=True).first.click()
            expect(controls.get_by_role('alert')).to_contain_text('cancelled', timeout=10000)
        finally:
            self.embedding_gate.set()
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT generation FROM memory_indexes').fetchone()[0], generation)

        # Hold a real old-scope status response until another project's view is loaded.
        held = []

        def delay_status(route):
            held.append((route, route.fetch()))

        page.route('**/memory/index?project=.', delay_status)
        page.get_by_role('button', name='Chat', exact=True).click()
        page.get_by_role('button', name='Project memory', exact=True).click()
        expect(controls).to_contain_text('Loading index status')
        chosen = str(self.policy.root / 'other')
        page.evaluate('(chosen)=>{const previous=window.__TAURI_INTERNALS__.invoke;'
                      'window.__TAURI_INTERNALS__.invoke=async(name,args)=>name==="plugin:dialog|open"?chosen:previous(name,args);}', chosen)
        page.get_by_role('button', name='Choose project', exact=True).click()
        expect(page.locator('.memory-page article')).to_contain_text('OTHER-SCOPE-PRIVATE-PARAGRAPH')
        expect(controls).to_contain_text('Not indexed')
        self.assertGreaterEqual(len(held), 1)
        for route, response in held:
            route.fulfill(response=response)
        page.unroute('**/memory/index?project=.', delay_status)
        page.wait_for_timeout(150)
        expect(controls).to_contain_text('Not indexed')
        expect(controls).not_to_contain_text('fixture-embedding')
        expect(controls.get_by_role('button', name='Enable related-note context', exact=True)).to_be_disabled()

    def test_related_files_share_review_and_display_both_artifact_records(self):
        self.run_profile_scenario(patch_set=True)

    def test_command_output_is_live_redacted_and_replayed_before_test_completion(self):
        self.run_profile_scenario(streaming=True)

    def test_cancel_preserves_safe_partial_command_output_without_verifying_tests(self):
        self.run_profile_scenario(streaming=True, cancel_stream=True)

    def test_background_readiness_is_visible_then_task_cleanup_stops_server(self):
        self.run_profile_scenario(background_case=True)

    def test_background_cancel_kills_owned_server_and_command(self):
        self.run_profile_scenario(background_case=True, cancel_stream=True)

    def run_profile_scenario(self, artifact=False, search=False, patch_set=False, streaming=False, cancel_stream=False,
                             background_case=False, diagnostics=False, journal=False, inference=False,
                             context_case=False, context_blocked=False, memory_case=False, scoped_case=False,
                             accessibility=False, conversation_case=False, message_case=False, task_case=False,
                             backup_case=False, restore_case=False, retention_case=False, inspection_case=False, semantic_case=False, memory_file_case=False):
        from playwright.sync_api import expect, sync_playwright
        owner = self

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if restore_case and self.path == '/fixture/connection':
                    data = json.dumps({'port': owner.port, 'token': owner.token}).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                super().do_GET()

            def do_POST(self):
                if not restore_case or self.path != '/fixture/restart' or self.headers.get('Origin') != 'http://127.0.0.1:1420':
                    self.send_error(404)
                    return
                try:
                    owner.stop_backend()
                    owner.start_backend()
                except (OSError, AssertionError, ValueError, TimeoutError) as exc:
                    owner.fixture_restart_error = str(exc)
                    self.send_error(500, 'Fixture restart failed')
                    return
                data = json.dumps({'port': owner.port, 'token': owner.token}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        try:
            server = ThreadingHTTPServer(("127.0.0.1", 1420),
                                         partial(Quiet, directory=str(Path("desktop/dist").resolve())))
        except OSError:
            if restore_case:
                raise RuntimeError('Restore UI fixture needs its own localhost1420 listener; close the development frontend first') from None
            with build_opener(ProxyHandler({})).open("http://127.0.0.1:1420/src/App.tsx", timeout=3) as response:
                self.assertIn("WorkspacePanel", response.read().decode())
        else:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        (self.policy.root / "sample.txt").write_text("profile acceptance", encoding="utf-8")
        if inspection_case:
            (self.policy.root / 'a.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
            (self.policy.root / 'b.py').write_text('from a import add\nassert add(2, 3) == 5\n', encoding='utf-8')
        (self.policy.root / "test_sample.py").write_text(
            "import unittest\nfrom pathlib import Path\nclass Readback(unittest.TestCase):\n"
            " def test_readback(self):\n  self.assertEqual(Path('sample.txt').read_text(), 'profile acceptance')\n",
            encoding="utf-8")
        if context_case:
            context_conversation = self.store.tasks()[0]["conversation"]
            old_context = "OLD-CONTEXT-CANARY assistant explanation. " * 1000
            self.store.message(context_conversation, "assistant", old_context)
        if memory_case:
            memory_chat = self.store.tasks()[0]["conversation"]
            source = self.store.message(memory_chat, "user", "Lavender message snapshot")
        if conversation_case:
            with self.store.connection() as db:
                db.executemany('INSERT INTO conversations(id,title,created) VALUES (?,?,?)',
                               [(f'history-chat-{i}', f'History chat {i:02}', i + 1) for i in range(71)])
            self.store.message('history-chat-0', 'user', 'OLDEST-TRANSCRIPT-CANARY')
        if message_case:
            self.store.message(self.store.tasks()[0]['conversation'], 'user', 'FOREIGN-MESSAGE-CANARY')
            self.message_chat = self.store.conversation('Message pages')
            attachment = self.store.attachment(self.message_chat, {'name': 'old.txt', 'mime': 'text/plain',
                'data': b'EXPORT-ATTACHMENT-BYTES', 'text': 'EXPORT-ATTACHMENT-BYTES'})
            for index in range(125):
                self.store.message(self.message_chat, 'user' if index % 2 == 0 else 'assistant',
                                   f'PAGE-MESSAGE-{index:03}', attachment_ids=[attachment['id']] if index == 0 else [])
        if task_case:
            self.history_chat = self.store.conversation('Historical project')
            self.store.message(self.history_chat, 'user', 'ARCHIVED-CONVERSATION')
            self.history_tasks = [self.store.task(self.history_chat, 'agent', f'historical-{i:03}') for i in range(250)]
            with self.store.connection() as db:
                for index, task in enumerate(self.history_tasks):
                    db.execute('UPDATE tasks SET status=?,result=?,created=?,journal_version=0 WHERE id=?',
                               ('reported', '{"report":"PRIVATE-HISTORY-RESULT"}', index + 1, task))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            if restore_case:
                page.add_init_script('window.__fixtureConnection=' + json.dumps({'port': self.port, 'token': self.token}) + ';'
                    'window.__TAURI_INTERNALS__={invoke:async(name)=>{if(name==="restart_backend"){'
                    'const response=await fetch("/fixture/restart",{method:"POST"});'
                    'if(!response.ok)throw new Error("Fixture restart failed");'
                    'window.__fixtureConnection=await response.json();window.__nativeRestarts=(window.__nativeRestarts||0)+1;}'
                    'else if(name==="backend_connection"){window.__fixtureConnection=await(await fetch("/fixture/connection")).json();}'
                    'else if(name==="backend_diagnostics"){return "Fixture native diagnostics";}'
                    'return window.__fixtureConnection;}};')
            else:
                page.add_init_script("window.__TAURI_INTERNALS__={invoke:async()=> (" +
                                     json.dumps({"port": self.port, "token": self.token}) + ")};")
            if message_case or task_case:
                page.add_init_script("window.__OriginalSocket=WebSocket; window.WebSocket=class extends window.__OriginalSocket {constructor(...args){super(...args);window.__UI_SOCKET=this;}};")
            submitted = []
            history_requests = []
            page.on('request', lambda request: history_requests.append(request.url)
                    if request.method == 'GET' and ('/conversations' in request.url or task_case) else None)
            page.on("request", lambda request: submitted.append(request.post_data_json)
                    if request.url.endswith("/slash") and request.method == "POST" else None)
            page.goto("http://127.0.0.1:1420")
            expect(page.locator(".local-status")).to_contain_text("Connected locally", timeout=15000)
            if memory_file_case:
                if memory_file_case == 'empty':
                    self.run_file_empty_conversation_scenario(page)
                elif memory_file_case in ('review', 'navigation'):
                    self.run_file_review_scenario(page, navigation=memory_file_case == 'navigation')
                else:
                    self.run_memory_file_scenario(page)
                browser.close()
                return
            if semantic_case:
                self.run_semantic_memory_scenario(page)
                browser.close()
                return
            if inspection_case:
                self.run_inspection_scenario(page)
                browser.close()
                return
            if restore_case:
                self.run_restore_scenario(page)
                browser.close()
                return
            if backup_case:
                self.run_backup_scenario(page)
                browser.close()
                return
            if retention_case:
                self.run_retention_scenario(page)
                browser.close()
                return
            if conversation_case:
                self.run_conversation_scenario(page, history_requests)
                browser.close()
                return
            if message_case:
                self.run_message_scenario(page, history_requests)
                browser.close()
                return
            if task_case:
                self.run_task_history_scenario(page, history_requests)
                browser.close()
                return
            if accessibility:
                self.run_accessibility_scenario(page)
                browser.close()
                return
            if scoped_case:
                self.run_scoped_scenario(page)
                browser.close()
                return
            if memory_case:
                page.get_by_role("button", name="WEBSOCKET-PRIVATE-CANARY", exact=True).click()
                if memory_case == "slash":
                    composer = page.get_by_role("textbox", name="Message", exact=True)
                    composer.fill("/remember Lavender slash note")
                    page.get_by_title("Send message", exact=True).click()
                    expect(page.locator(".memory-page article")).to_have_count(1)
                    ident = self.http('/memory')[0]['id']
                    page.get_by_role("button", name="Chat", exact=True).click()
                    composer.fill("/recall Lavender")
                    page.get_by_title("Send message", exact=True).click()
                    expect(page.locator(".memory-page article")).to_contain_text("Lavender slash note")
                    for confirmed in (False, True):
                        page.get_by_role("button", name="Chat", exact=True).click()
                        composer.fill("/forget " + ident)
                        page.get_by_title("Send message", exact=True).click()
                        expect(page.get_by_role("dialog")).to_contain_text("Forget this memory?")
                        page.get_by_role("button", name="Forget memory" if confirmed else "Cancel", exact=True).click()
                        expect(page.get_by_role("dialog")).to_have_count(0)
                        page.get_by_role("button", name="Chat", exact=True).click()
                        page.get_by_role("button", name="Project memory", exact=True).click()
                        expect(page.get_by_role("dialog")).to_have_count(0)
                        expect(page.locator(".memory-page [role=alert]")).to_have_count(0)
                    expect(page.locator(".memory-page article")).to_have_count(0)
                    self.assertEqual(self.http('/memory'), [])
                    self.assertFalse(self.inference_requests)
                    browser.close()
                    return
                page.get_by_role("button", name="Project memory", exact=True).click()
                page.get_by_label("Memory note", exact=True).fill("Lavender compiler uses flag amber")
                page.get_by_role("button", name="Remember", exact=True).click()
                expect(page.locator(".memory-page article")).to_have_count(1)
                page.get_by_label("Memory source", exact=True).select_option(source)
                page.get_by_role("button", name="Remember", exact=True).click()
                expect(page.locator(".memory-page article")).to_have_count(2)
                page.get_by_label("Search project memory", exact=True).fill("compiler")
                page.get_by_role("button", name="Search", exact=True).click()
                articles = page.locator(".memory-page article")
                expect(articles).to_have_count(1)
                expect(articles).to_contain_text("SHA-256")
                articles.get_by_role("button", name="Forget", exact=True).click()
                expect(page.get_by_role("dialog")).to_contain_text("Visible chat transcripts remain")
                page.get_by_role("button", name="Cancel", exact=True).click()
                self.assertEqual(len(self.http('/memory')), 2)
                articles.get_by_role("button", name="Forget", exact=True).click()
                page.get_by_role("button", name="Forget memory", exact=True).click()
                expect(articles).to_have_count(0)
                self.assertEqual(len(self.http('/memory')), 1)
                page.get_by_role("button", name="Delete WEBSOCKET-PRIVATE-CANARY", exact=True).click()
                expect(page.get_by_role("dialog")).to_contain_text("saved memories")
                page.get_by_role("button", name="Delete conversation", exact=True).click()
                expect(page.get_by_role("dialog")).to_have_count(0)
                page.reload()
                expect(page.locator(".local-status")).to_contain_text("Connected locally", timeout=15000)
                page.get_by_role("button", name="Project memory", exact=True).click()
                expect(page.locator(".memory-page article")).to_have_count(0)
                self.assertEqual(self.http('/memory'), [])
                self.assertFalse(self.inference_requests)
                browser.close()
                return
            if context_case:
                page.get_by_role("button", name="WEBSOCKET-PRIVATE-CANARY", exact=True).click()
            if context_blocked:
                page.get_by_role("button", name="Models & settings", exact=True).click()
                page.get_by_label("Context window", exact=True).select_option("2048")
                page.get_by_label("Maximum output tokens", exact=True).fill("2048")
            if inference:
                page.get_by_role("button", name="Models & settings", exact=True).click()
                expect(page.get_by_text("Advertised:", exact=False)).to_contain_text("completion", timeout=15000)
                page.get_by_label("Maximum output tokens", exact=True).fill("517")
                page.get_by_label("Context window", exact=True).select_option("4096")
                page.get_by_label("Thinking", exact=True).select_option("true")
                page.get_by_label("Keep model loaded", exact=True).select_option("60s")
            if search:
                page.get_by_role("button", name="Workspace", exact=True).click()
                query = page.get_by_role("textbox", name="Search project text", exact=True)
                query.fill("profile acceptance")
                page.get_by_role("button", name="Search project", exact=True).click()
                results = page.locator(".repository-results")
                expect(results).to_contain_text("sample.txt:1:1")
                page.get_by_title("Open sample.txt at matching line 1", exact=True).click()
                expect(page.locator(".code-title")).to_have_text("sample.txt")
                expect(page.locator(".code-view pre")).to_have_text("profile acceptance")
                (self.policy.root / "many.txt").write_text("needle\n" * 100, encoding="utf-8")
                query.fill("needle")
                page.get_by_role("button", name="Search project", exact=True).click()
                expect(results).to_contain_text("Incomplete: output limit")
                self.assertEqual(len(self.http("/tasks")["tasks"]), 1)
                self.assertFalse(self.inference_requests)
                browser.close()
                return
            page.get_by_role("button", name="Agent", exact=True).click()
            profile = page.get_by_role("combobox", name="Tool access")
            expect(profile).to_have_value("unified")
            if streaming or background_case:
                (self.policy.root / "test_sample.py").write_text(
                    "import unittest,time\nfrom pathlib import Path\nclass Streaming(unittest.TestCase):\n"
                    " def test_live(self):\n  print('LIVE-COMMAND '+'.'*40)\n"
                    "  print('<script>window.COMMAND_XSS=1</script>')\n  print('password=STREAM-UI-CANARY')\n"
                    "  while not Path('release-test').exists():time.sleep(.02)\n  self.assertTrue(True)\n", encoding="utf-8")
                profile.select_option("coding")
                title = "Run background readiness fixture" if background_case else "/test"
                if background_case:
                    (self.policy.root / "ui-background.py").write_text(server_source(self.background_port), encoding="utf-8")
                page.get_by_role("textbox", name="Message", exact=True).fill(title)
                page.get_by_title("Send message", exact=True).click()
                if background_case:
                    expect(page.get_by_role("dialog")).to_contain_text("start code", timeout=15000)
                    expect(page.get_by_role("dialog")).to_contain_text(f"127.0.0.1:{self.background_port}/health")
                    page.get_by_role("button", name="Approve action", exact=True).click()
                    expect(page.get_by_role("region", name="Command output", exact=True)).to_contain_text("Readiness: ready observed",
                                                                                                                       timeout=15000)
                expect(page.get_by_role("dialog")).to_contain_text("execute code", timeout=15000)
                page.get_by_role("button", name="Approve action", exact=True).click()
                output = page.get_by_role("region", name="Command output", exact=True)
                expect(output).to_contain_text("LIVE-COMMAND", timeout=15000)
                expect(output).to_contain_text("Running")
                row = next(row for row in self.http("/tasks")["tasks"] if row["id"] != self.task)
                self.assertEqual(row["status"], "running")
                page.reload()
                expect(page.locator(".local-status")).to_contain_text("Connected locally", timeout=15000)
                # Reload opens a blank chat; select the task's persisted conversation.
                page.get_by_role("button", name=title, exact=True).click()
                expect(output).to_contain_text("LIVE-COMMAND", timeout=15000)
                self.assertEqual(output.inner_text().count("LIVE-COMMAND"), 1)
                self.assertNotIn("STREAM-UI-CANARY", output.inner_text())
                self.assertIsNone(page.evaluate("window.COMMAND_XSS"))
                if cancel_stream:
                    page.get_by_title("Cancel current task", exact=True).click()
                    expect(output).to_contain_text("Interrupted; final command status unavailable", timeout=15000)
                    self.assertFalse(self.http(f"/tasks/{row['id']}/verifications"))
                    self.assertEqual(next(t for t in self.http("/tasks")["tasks"] if t["id"] == row["id"])["status"], "cancelled")
                else:
                    (self.policy.root / "release-test").touch()
                    expect(output).to_contain_text("Exited 0", timeout=15000)
                    expect(page.locator(".event-list")).to_contain_text("Test run: passed", timeout=15000)
                    self.assertEqual(self.http(f"/tasks/{row['id']}/verifications")[0]["counts"]["tests_run"], 1)
                if background_case:
                    import psutil

                    if not cancel_stream:
                        expect(output).to_contain_text("Readiness: stopped", timeout=15000)
                    pid = int((self.policy.root / "server.pid").read_text())
                    try:
                        psutil.Process(pid).wait(timeout=2)
                    except psutil.NoSuchProcess:
                        pass
                    self.assertNotIn("BACKGROUND-SECRET-CANARY", output.inner_text())
                else:
                    self.assertFalse(self.inference_requests)
                browser.close()
                return
            if patch_set:
                profile.select_option("coding")
                page.get_by_role("textbox", name="Message", exact=True).fill("Apply reviewed patch set")
                page.get_by_title("Send message", exact=True).click()
                dialog = page.get_by_role("dialog")
                expect(dialog).to_contain_text("apply patch set", timeout=15000)
                expect(dialog).to_contain_text('"path": "sample.txt"')
                expect(dialog).to_contain_text('"path": "related.txt"')
                expect(dialog).to_contain_text("not as a crash-atomic transaction")
                self.assertEqual((self.policy.root / "sample.txt").read_bytes(), b"profile acceptance")
                self.assertFalse((self.policy.root / "related.txt").exists())
                page.get_by_role("button", name="Approve action", exact=True).click()
                expect(page.locator(".event-list strong").filter(has_text="Artifact readback: passed")).to_have_count(2,
                                                                                                                         timeout=15000)
                self.assertEqual((self.policy.root / "sample.txt").read_bytes(), b"reviewed patch")
                self.assertEqual((self.policy.root / "related.txt").read_bytes(), b"related patch")
                row = next(row for row in self.http("/tasks")["tasks"] if row["id"] != self.task)
                checks = self.http(f"/tasks/{row['id']}/verifications")
                self.assertEqual(len(checks), 2)
                self.assertTrue(all(check["status"] == "passed" for check in checks))
                browser.close()
                return
            if artifact:
                profile.select_option("coding")
                page.get_by_role("textbox", name="Message", exact=True).fill("Create the reviewed artifact")
                page.get_by_title("Send message", exact=True).click()
                if context_blocked:
                    expect(page.locator(".message.assistant").last).to_contain_text("Context cannot fit", timeout=15000)
                    panel = page.locator(".context-budget")
                    expect(panel).to_contain_text("blocked")
                    panel.locator("summary").click()
                    expect(panel).to_contain_text("reduce maximum output")
                    expect(page.get_by_role("dialog")).to_have_count(0)
                    self.assertFalse((self.policy.root / "artifact.txt").exists())
                    self.assertFalse(self.inference_requests)  # Compatibility probe is separate.
                    row = next(row for row in self.http("/tasks")["tasks"] if row["id"] != self.task)
                    self.assertEqual(self.http(f"/tasks/{row['id']}/journal")["operations"], [])
                    browser.close()
                    return
                expect(page.get_by_role("dialog")).to_contain_text("create file", timeout=15000)
                page.get_by_role("button", name="Approve action", exact=True).click()
                expect(page.locator(".event-list")).to_contain_text("Artifact readback: passed", timeout=15000)
                row = next(row for row in self.http("/tasks")["tasks"] if row["id"] != self.task)
                checks = self.http(f"/tasks/{row['id']}/verifications")
                self.assertEqual(checks[0]["kind"], "artifact")
                self.assertEqual(checks[0]["observed_sha256"], hashlib.sha256(b"reviewed fixture").hexdigest())
                self.assertEqual((self.policy.root / "artifact.txt").read_bytes(), b"reviewed fixture")
                self.assertTrue(self.inference_requests)  # Protocol fixture, not Ollama inference.
                if context_case:
                    panel = page.locator(".context-budget")
                    expect(panel).to_contain_text("compacted", timeout=15000)
                    panel.locator("summary").click()
                    expect(panel).to_contain_text("Estimate, not an exact tokenizer count")
                    expect(panel).to_contain_text("Instructions and original images are preserved")
                    self.assertNotIn("OLD-CONTEXT-CANARY", panel.inner_text())
                    self.assertEqual(self.store.messages(context_conversation)[0]["content"], old_context)
                    expect(page.locator(".activity-status strong")).to_have_text("Ready", timeout=15000)
                    page.get_by_role("button", name="New conversation", exact=True).click()
                    expect(page.locator(".context-budget")).to_have_count(0)
                if inference:
                    page.locator(".response-metrics").last.locator("summary").click()
                    expect(page.locator(".response-metrics").last).to_contain_text("Call 1: stop", timeout=15000)
                    expect(page.locator(".response-metrics").last).to_contain_text("prompt 12 tokens")
                    expect(page.locator(".response-metrics").last).to_contain_text("load 0.02s")
                    expect(page.locator(".response-metrics").last).to_contain_text("Compatibility checks: 1")
                    for body in self.inference_requests:
                        self.assertEqual(body["options"]["num_predict"], 517)
                        self.assertEqual(body["options"]["num_ctx"], 4096)
                        self.assertIs(body["think"], True)
                        self.assertEqual(body["keep_alive"], "60s")
                    preferences = self.http("/preferences")
                    self.assertEqual(preferences["max_output"], 517)
                    self.assertEqual(preferences["keep_alive"], "60s")
                    self.assertIs(preferences["thinking"], True)
                if diagnostics:
                    expect(page.locator(".activity-status strong")).to_have_text("Ready", timeout=15000)
                    page.get_by_role("button", name="Task history", exact=True).click()
                    panel = page.locator(".task-diagnostics").first
                    panel.locator("summary").first.click()
                    panel.get_by_role("button", name="Load diagnostics", exact=True).click()
                    expect(panel).to_contain_text("Trace captured; whole-task verification is not assessed.", timeout=15000)
                    expect(panel).to_contain_text("1 verifier observations")
                    expect(panel).to_contain_text("Tool outcomes: observed: 1")
                    expect(panel).to_contain_text("artifact: passed")
                    with page.expect_download() as saved:
                        panel.get_by_role("button", name="Download diagnostic JSON", exact=True).click()
                    content = Path(saved.value.path()).read_text(encoding="utf-8")
                    exported = json.loads(content)
                    self.assertEqual(exported["run_id"], row["id"])
                    self.assertFalse(exported["partial"])
                    self.assertEqual(exported["verifications"][0]["id"], checks[0]["id"])
                    for forbidden in (self.token, "reviewed fixture", "artifact.txt", self.config["model"]["name"]):
                        self.assertNotIn(forbidden, content)
                    self.assertLess(len(content.encode()), 1024 * 1024)
                if journal:
                    expect(page.locator(".activity-status strong")).to_have_text("Ready", timeout=15000)
                    if journal == "unknown":
                        # Explicit persisted-state UI fixture; actual os._exit boundaries
                        # are exercised separately by JournalProcessTests.
                        import uuid

                        from local_agent.observability import Trace
                        from local_agent.studio.journal import Preconditions, digest, scope_key
                        task = self.store.task(row["conversation"], "agent", row["model"],
                                               project=".", scope_key=scope_key(self.policy.root))
                        records = []
                        trace = Trace(task, self.config["model"], records.append)
                        trace.start("run")
                        step = trace.start("step", index=1)
                        self.store.record_step(task, records[-1])
                        arguments = {"path": "artifact.txt", "text": "reviewed fixture"}
                        operation = {"version": 1, "id": uuid.uuid4().hex, "step": step.record["id"],
                                     "tool": "write_file", "effect": "filesystem", "arguments_sha256": digest(arguments),
                                     "preconditions": Preconditions(self.policy, "write_file", arguments).public}
                        self.store.operation_intent(task, operation)
                        self.store.recover()
                        page.reload()
                        expect(page.locator(".local-status")).to_contain_text("Connected locally", timeout=15000)
                    page.get_by_role("button", name="Task history", exact=True).click()
                    panel = page.locator(".task-journal").first
                    panel.locator("summary").first.click()
                    panel.get_by_role("button", name="Load execution journal", exact=True).click()
                    expect(panel).to_contain_text("Decision 1 · unknown" if journal == "unknown" else "Decision 1 · completed", timeout=15000)
                    expect(panel).to_contain_text("write_file · filesystem · unknown" if journal == "unknown" else "write_file · filesystem · result observed · observed")
                    panel.get_by_role("button", name="Inspect current artifacts", exact=True).click()
                    expect(panel.locator(".journal-inspection")).to_contain_text("matches proposed: yes", timeout=15000)
                    expect(panel.locator(".journal-inspection")).to_contain_text("matches recorded: yes" if journal == "unknown" else "matches recorded: no")
                    (self.policy.root / "artifact.txt").write_text("user changed", encoding="utf-8")
                    panel.get_by_role("button", name="Inspect current artifacts", exact=True).click()
                    expect(panel.locator(".journal-inspection")).to_contain_text("matches proposed: no", timeout=15000)
                    count = len(self.http("/tasks")["tasks"])
                    requests_before = len(self.inference_requests)
                    panel.get_by_role("button", name="Write a new instruction", exact=True).click()
                    expect(page.get_by_role("textbox", name="Message", exact=True)).to_be_focused()
                    expect(page.get_by_role("alert")).to_contain_text("fresh run with fresh approvals")
                    expect(page.get_by_role("dialog")).to_have_count(0)
                    self.assertEqual(len(self.http("/tasks")["tasks"]), count)
                    self.assertEqual(len(self.inference_requests), requests_before)
                    self.assertEqual((self.policy.root / "artifact.txt").read_text(), "user changed")
                    if journal == "unknown":
                        self.assertEqual(self.http(f"/tasks/{task}/journal")["operations"][0]["state"], "unknown")
                browser.close()
                return
            profile.select_option("browser")
            composer = page.get_by_role("textbox", name="Message", exact=True)
            composer.fill("/test")
            page.get_by_title("Send message", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("requires a profile with coding tools")
            self.assertEqual(submitted[-1]["profile"], "browser")
            self.assertEqual(len(self.http("/tasks")["tasks"]), 1)  # Only the harness seed task.
            page.get_by_title("Dismiss notification").click()
            profile.select_option("coding")
            composer.fill("/test")
            page.get_by_title("Send message", exact=True).click()
            expect(page.get_by_role("dialog")).to_contain_text("execute code", timeout=15000)
            expect(profile).to_be_disabled()
            page.get_by_role("button", name="Approve action", exact=True).click()
            expect(page.locator(".message.assistant .message-body").last).to_contain_text("Ran 1 test", timeout=15000)
            expect(page.locator(".message.assistant .message-body").last).to_contain_text("OK")
            row = next(row for row in self.http("/tasks")["tasks"] if row["id"] != self.task)
            self.assertEqual(row["profile"], "coding")
            self.assertEqual(row["status"], "reported")
            expect(page.locator(".event-list")).to_contain_text("Test run: passed")
            checks = self.http(f"/tasks/{row['id']}/verifications")
            self.assertEqual(checks[0]["status"], "passed")
            self.assertEqual(checks[0]["counts"]["tests_run"], 1)
            self.assertEqual(submitted[-1]["profile"], "coding")
            self.assertFalse(self.inference_requests)
            browser.close()

    def run_restore_scenario(self, page):
        from playwright.sync_api import expect

        chat = self.store.tasks()[0]['conversation']
        self.store.message(chat, 'user', 'SAVED-STATE-MESSAGE')
        page.get_by_role('button', name='WEBSOCKET-PRIVATE-CANARY', exact=True).click()
        expect(page.locator('.messages')).to_contain_text('SAVED-STATE-MESSAGE')
        page.get_by_role('button', name='Models & settings', exact=True).click()
        with page.expect_response(lambda response: response.url.endswith('/preferences')
                and response.request.method == 'POST' and response.request.post_data_json.get('context') == 4096):
            page.get_by_label('Context window', exact=True).select_option('4096')
        panel = page.locator('.backup-panel')
        inventory_url = f'http://127.0.0.1:{self.port}/backups'
        old_inventory = []

        def hold_inventory(route):
            if route.request.method == 'GET' and not old_inventory:
                response = route.fetch()
                self.assertEqual(response.json()['items'], [])
                old_inventory.append((route, response))
            else:
                route.continue_()

        page.route(inventory_url, hold_inventory)
        panel.get_by_role('button', name='Refresh backups', exact=True).click()
        panel.get_by_role('button', name='Create Studio backup', exact=True).click()
        page.get_by_role('button', name='Save backup', exact=True).click()
        expect(panel.get_by_role('status')).to_contain_text('Backup saved:')
        saved = self.http('/backups')['items'][0]
        self.assertEqual(len(old_inventory), 1)
        with page.expect_event('requestfinished', predicate=lambda request: request.url == inventory_url and request.method == 'GET'):
            old_inventory[0][0].fulfill(response=old_inventory[0][1])
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        expect(panel.get_by_label('Saved backup', exact=True).locator(f'option[value="{saved["id"]}"]')).to_have_count(1)
        page.get_by_role('button', name='Chat', exact=True).click()
        page.locator('.new-chat').click()
        expect(page.locator('.conversation-row.selected')).to_contain_text('New conversation')
        page.get_by_role('textbox', name='Message', exact=True).fill('UNSENT-BEFORE-RESTORE')
        page.locator('input[type=file]').set_input_files({'name': 'newer.txt', 'mimeType': 'text/plain', 'buffer': b'NEWER-ATTACHMENT'})
        expect(page.get_by_title('Preview newer.txt', exact=True)).to_be_visible()
        newer = self.http('/history/conversations')['items'][0]['id']
        self.store.rename_conversation(newer, 'Newer UI data')
        self.store.message(newer, 'assistant', 'NEWER-VISIBLE-MESSAGE')
        page.get_by_role('button', name='Models & settings', exact=True).click()
        with page.expect_response(lambda response: response.url.endswith('/preferences')
                and response.request.method == 'POST' and response.request.post_data_json.get('context') == 16384):
            page.get_by_label('Context window', exact=True).select_option('16384')
        old_preferences = f'http://127.0.0.1:{self.port}/preferences'
        held = []

        def hold_preferences(route):
            if route.request.method == 'GET' and not held:
                response = route.fetch()
                self.assertEqual(response.json()['context'], 16384)
                held.append((route, response))
            else:
                route.continue_()

        page.route(old_preferences, hold_preferences)
        page.reload()
        expect(page.locator('.local-status')).to_contain_text('Connected locally')
        page.get_by_role('button', name='Newer UI data', exact=True).click()
        expect(page.get_by_title('Preview newer.txt', exact=True)).to_be_visible()
        page.get_by_role('textbox', name='Message', exact=True).fill('UNSENT-AFTER-RELOAD')
        page.get_by_role('button', name='Models & settings', exact=True).click()
        panel.get_by_label('Saved backup', exact=True).select_option(saved['id'])
        panel.get_by_role('button', name='Inspect backup', exact=True).click()
        expect(panel).to_contain_text('Inspected SHA-256:')
        restore = panel.get_by_role('button', name='Restore selected backup', exact=True)
        page.set_viewport_size({'width': 900, 'height': 900})
        restore.click()
        dialog = page.get_by_role('dialog')
        expect(dialog).to_contain_text('The backend will restart')
        page.keyboard.press('Tab')
        expect(dialog.get_by_role('button', name='Restore and restart', exact=True)).to_be_focused()
        page.keyboard.press('Shift+Tab')
        expect(dialog.get_by_role('button', name='Cancel', exact=True)).to_be_focused()
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(restore).to_be_focused()
        self.assertFalse((self.policy.state / 'restore-staging').exists())
        self.assertIsNone(self.http('/restore/status')['generation'])
        self.assertEqual(len(held), 1)
        restore.click()
        page.get_by_role('button', name='Restore and restart', exact=True).click()
        expect(panel).to_contain_text('Restored data is active.', timeout=20000)
        expect(page.locator('.local-status')).to_contain_text('Connected locally')
        expect(page.get_by_label('Context window', exact=True)).to_have_value('4096')
        self.assertEqual(page.evaluate('window.__nativeRestarts'), 1)
        self.assertEqual(self.http('/preferences')['context'], 4096)
        with page.expect_event('requestfinished', predicate=lambda request: request.url == old_preferences and request.method == 'GET'):
            held[0][0].fulfill(response=held[0][1])
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        expect(page.get_by_label('Context window', exact=True)).to_have_value('4096')
        self.assertEqual(self.http('/preferences')['context'], 4096)
        expect(page.locator('.conversation-row')).to_have_count(1)
        expect(page.locator('.conversation-row')).not_to_contain_text('Newer UI data')
        page.locator('.settings-page').screenshot(path=str(Path('.runtime/p1-06-restore-activation/restore-settings.png').resolve()))
        page.get_by_role('button', name='Chat', exact=True).click()
        expect(page.get_by_role('textbox', name='Message', exact=True)).to_have_value('')
        expect(page.get_by_title('Preview newer.txt', exact=True)).to_have_count(0)
        page.get_by_role('button', name='WEBSOCKET-PRIVATE-CANARY', exact=True).click()
        expect(page.locator('.messages')).to_contain_text('SAVED-STATE-MESSAGE')
        expect(page.get_by_role('textbox', name='Message', exact=True)).to_have_value('')
        expect(page.get_by_title('Preview newer.txt', exact=True)).to_have_count(0)
        expect(page.get_by_role('alert').filter(has_text='Resource not found')).to_have_count(0)
        page.get_by_role('button', name='Models & settings', exact=True).click()
        panel.get_by_role('button', name='Restore previous state', exact=True).click()
        expect(dialog).to_contain_text('Restore previous Studio state?')
        page.get_by_role('button', name='Restore and restart', exact=True).click()
        expect(panel).to_contain_text('Restored data is active.', timeout=20000)
        expect(page.get_by_label('Context window', exact=True)).to_have_value('16384')
        self.assertEqual(page.evaluate('window.__nativeRestarts'), 2)
        page.get_by_role('button', name='Chat', exact=True).click()
        expect(page.get_by_role('textbox', name='Message', exact=True)).to_have_value('')
        page.get_by_role('button', name='Newer UI data', exact=True).click()
        expect(page.locator('.messages')).to_contain_text('NEWER-VISIBLE-MESSAGE')
        expect(page.get_by_title('Preview newer.txt', exact=True)).to_be_visible()
        expect(page.get_by_role('textbox', name='Message', exact=True)).to_have_value('')
        self.assertEqual(len(self.store.conversations()), 2)
        self.assertFalse(self.inference_requests)
        self.assertFalse((self.policy.root / 'artifact.txt').exists())
        self.assertFalse(getattr(self, 'fixture_restart_error', ''))

    def run_inspection_scenario(self, page):
        from playwright.sync_api import expect

        requests = self.inference_requests
        page.get_by_role('button', name='Workspace', exact=True).click()
        panel = page.get_by_role('region', name='Resumable repository inspection', exact=True)
        panel.locator('summary').click()
        panel.get_by_label('Inspection files', exact=True).fill('a.py\nb.py')
        panel.get_by_label('Inspection question', exact=True).fill('Explain the selected code and potential bugs')
        panel.get_by_role('button', name='Start read-only inspection', exact=True).click()
        pause = panel.get_by_role('button', name='Pause at next inspection boundary', exact=True)
        expect(pause).to_be_enabled(timeout=15000)
        original = self.http('/tasks')['tasks'][0]['id']
        self.assertEqual(self.http(f'/tasks/{original}/inspection')['completed_step'], 1)
        pause.click()
        expect(panel).to_contain_text('Pause requested; waiting')
        expect(panel).not_to_contain_text('Checkpoint: paused')
        self.inspection_gate.set()
        resume = panel.get_by_role('button', name='Resume inspected files', exact=True)
        expect(resume).to_be_enabled(timeout=15000)
        expect(panel).to_contain_text('Checkpoint: paused')
        self.assertEqual(self.http('/tasks')['tasks'][0]['status'], 'interrupted')
        # Real owned backend exit/restart through the existing native-IPC fixture bridge.
        self.stop_backend()
        restart = page.get_by_role('button', name='Restart backend', exact=True)
        expect(restart).to_be_visible(timeout=15000)
        restart.click()
        expect(page.locator('.local-status')).to_contain_text('Connected locally', timeout=15000)
        page.get_by_role('button', name='Task history', exact=True).click()
        page.locator('.history-row').filter(has_text='inspection').first.click()
        expect(resume).to_be_enabled(timeout=15000)
        expect(panel).to_contain_text('Checkpoint: paused')
        page.get_by_role('combobox', name='Tool access').select_option('unified')
        before = len(requests)
        resume.click()
        expect(panel).to_contain_text('Checkpoint: closed', timeout=15000)
        new_task = self.http('/tasks')['tasks'][0]
        self.assertNotEqual(new_task['id'], original)
        self.assertEqual(new_task['profile'], 'coding')
        self.assertEqual(new_task['status'], 'reported')
        self.assertEqual(len(requests) - before, 1)
        self.assertEqual({tool['function']['name'] for tool in requests[-1]['tools']}, {'read_file'})
        self.assertEqual(self.http(f'/tasks/{new_task["id"]}/journal')['operations'], [])
        self.assertFalse((self.policy.root / 'artifact.txt').exists())
        self.assertFalse(getattr(self, 'fixture_restart_error', ''))
        page.set_viewport_size({'width': 900, 'height': 1000})
        panel.locator('.inspection-state').scroll_into_view_if_needed()
        page.screenshot(path='.runtime/p2-01-checkpoints/inspection-workspace.png')

    def run_retention_scenario(self, page):
        from playwright.sync_api import expect

        kept = self.store.tasks()[0]['conversation']
        old = self.store.conversation('Retention old A')
        other = self.store.conversation('Retention old B')
        for chat in (kept, old, other):
            self.store.message(chat, 'user', 'RETENTION-PRIVATE-BODY')
        with self.store.connection() as db:
            for table in ('conversations', 'messages', 'tasks', 'events'):
                db.execute(f'UPDATE {table} SET created=1')
        canary = self.policy.root / 'retention-project.txt'
        canary.write_bytes(b'PRESERVE-PROJECT')
        page.reload()
        expect(page.locator('.local-status')).to_contain_text('Connected locally')
        page.get_by_role('button', name='WEBSOCKET-PRIVATE-CANARY', exact=True).click()
        page.get_by_role('button', name='Models & settings', exact=True).click()
        panel = page.locator('.retention-panel')
        panel.get_by_label('Retention age in days', exact=True).fill('1')
        panel.get_by_label('Retention recent conversations', exact=True).fill('0')
        panel.get_by_label('Retention batch size', exact=True).fill('1')
        preview = panel.get_by_role('button', name='Preview retention', exact=True)
        expect(preview).to_be_disabled()
        panel.get_by_role('button', name='Save retention settings', exact=True).click()
        expect(panel.get_by_role('status')).to_contain_text('No conversations were deleted')
        self.assertEqual(len(self.store.conversations()), 3)
        preview.click()
        evidence = panel.locator('.retention-preview')
        expect(evidence).to_contain_text('Retention old A')
        expect(evidence).not_to_contain_text('WEBSOCKET-PRIVATE-CANARY')
        expect(evidence).not_to_contain_text('RETENTION-PRIVATE-BODY')
        expect(evidence).to_contain_text('More eligible conversations remain')
        review = panel.get_by_role('button', name='Review retention deletion', exact=True)
        page.set_viewport_size({'width': 900, 'height': 900})
        review.click()
        dialog = page.get_by_role('dialog')
        expect(dialog).to_contain_text('Project files and saved backups remain')
        page.keyboard.press('Tab')
        expect(dialog.get_by_role('button', name='Delete reviewed conversations', exact=True)).to_be_focused()
        page.keyboard.press('Shift+Tab')
        expect(dialog.get_by_role('button', name='Cancel', exact=True)).to_be_focused()
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(review).to_be_focused()
        self.assertEqual(len(self.store.conversations()), 3)
        self.store.rename_conversation(old, 'Retention stale A')
        review.click()
        dialog.get_by_role('button', name='Delete reviewed conversations', exact=True).click()
        expect(panel.get_by_role('alert')).to_contain_text('data changed')
        expect(evidence).to_have_count(0)
        self.assertEqual(len(self.store.conversations()), 3)
        preview.click()
        expect(evidence).to_contain_text('Retention stale A')
        review.click()
        dialog.get_by_role('button', name='Delete reviewed conversations', exact=True).click()
        expect(panel.get_by_role('status')).to_contain_text('Deleted 1 conversations')
        self.assertEqual({row['id'] for row in self.store.conversations()}, {kept, other})
        expect(page.locator('.conversation-row.selected')).to_contain_text('WEBSOCKET-PRIVATE-CANARY')
        expect(page.get_by_role('button', name='Retention stale A', exact=True)).to_have_count(0)
        self.assertEqual(canary.read_bytes(), b'PRESERVE-PROJECT')
        self.assertFalse(self.inference_requests)
        page.reload()
        expect(page.locator('.local-status')).to_contain_text('Connected locally')
        page.get_by_role('button', name='Models & settings', exact=True).click()
        expect(panel.get_by_label('Retention batch size', exact=True)).to_have_value('1')
        expect(panel).to_contain_text('Last recorded batch: 1 conversations')
        expect(evidence).to_have_count(0)
        # A delayed real preview must not survive a change of protected selection.
        held = []
        url = f'http://127.0.0.1:{self.port}/retention/preview'

        def hold_preview(route):
            held.append((route, route.fetch()))
            page.evaluate('window.__RETENTION_HELD=true')

        page.route(url, hold_preview)
        preview.click()
        page.wait_for_function('window.__RETENTION_HELD===true')
        page.get_by_role('button', name='Retention old B', exact=True).click()
        with page.expect_event('requestfinished', predicate=lambda request: request.url == url):
            held[0][0].fulfill(response=held[0][1])
        page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        expect(evidence).to_have_count(0)
        expect(page.locator('.conversation-row.selected')).to_contain_text('Retention old B')
        self.assertEqual(len(self.store.conversations()), 2)
        panel.scroll_into_view_if_needed()
        page.screenshot(path='.runtime/p1-06-retention/retention-settings.png')
        # Actual owned execution and its approval wait protect retention globally.
        response = page.request.post(f'http://127.0.0.1:{self.port}/tasks',
            headers={'Authorization': 'Bearer ' + self.token}, data={
                'conversation': kept, 'mode': 'agent', 'model': self.config['model']['name'],
                'objective': 'Create reviewed fixture'})
        self.assertTrue(response.ok, response.text())
        expect(dialog).to_contain_text('create file')
        expect(preview).to_be_disabled()
        denied = page.request.post(f'http://127.0.0.1:{self.port}/retention/preview',
            headers={'Authorization': 'Bearer ' + self.token}, data={'protected': [other]})
        self.assertEqual(denied.status, 400)
        self.assertIn('owned tasks', denied.text())
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(preview).to_be_enabled(timeout=15000)
        self.assertFalse((self.policy.root / 'artifact.txt').exists())
        self.assertEqual(canary.read_bytes(), b'PRESERVE-PROJECT')
        self.assertEqual(len(self.store.conversations()), 2)

    def run_backup_scenario(self, page):
        import sqlite3
        from contextlib import closing

        from playwright.sync_api import expect

        from local_agent.studio.backups import validate

        root = self.policy.state / 'backups'
        page.get_by_role('button', name='Models & settings', exact=True).click()
        button = page.get_by_role('button', name='Create Studio backup', exact=True)
        button.click()
        dialog = page.get_by_role('dialog')
        expect(dialog).to_contain_text('unencrypted')
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(button).to_be_focused()
        self.assertFalse(root.exists())
        self.assertFalse(self.inference_requests)
        button.click()
        page.get_by_role('button', name='Save backup', exact=True).click()
        panel = page.locator('.backup-panel')
        expect(panel.get_by_role('status')).to_contain_text('Backup saved:')
        paths = list(root.glob('*.sqlite3'))
        self.assertEqual(len(paths), 1)
        with closing(sqlite3.connect(paths[0])) as saved:
            self.assertEqual(validate(saved), self.store.identity)
            self.assertEqual(saved.execute('SELECT title FROM conversations').fetchone()[0], 'WEBSOCKET-PRIVATE-CANARY')
        expect(panel.get_by_role('status')).to_contain_text(hashlib.sha256(paths[0].read_bytes()).hexdigest())
        expect(panel.get_by_role('button', name='Restore selected backup', exact=True)).to_be_enabled()
        self.assertFalse(self.inference_requests)
        conversation = self.store.tasks()[0]['conversation']
        response = page.request.post(f'http://127.0.0.1:{self.port}/tasks',
            headers={'Authorization': 'Bearer ' + self.token}, data={
                'conversation': conversation, 'mode': 'agent', 'model': self.config['model']['name'],
                'objective': 'Create reviewed fixture'})
        self.assertTrue(response.ok, response.text())
        expect(dialog).to_contain_text('create file')
        expect(button).to_be_disabled()
        # Actual authenticated endpoint still refuses if a caller bypasses the disabled button.
        denied = page.request.post(f'http://127.0.0.1:{self.port}/backups',
            headers={'Authorization': 'Bearer ' + self.token}, data={'confirmed': True})
        self.assertEqual(denied.status, 400)
        self.assertIn('active task', denied.text())
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(button).to_be_enabled(timeout=15000)
        self.assertFalse((self.policy.root / 'artifact.txt').exists())
        self.assertEqual(len(list(root.iterdir())), 1)

    def run_task_history_scenario(self, page, requests):
        from urllib.parse import urlsplit

        from playwright.sync_api import expect

        page.get_by_role('button', name='Task history', exact=True).click()
        rows = page.locator('.history-row')
        older = page.get_by_role('button', name='Older tasks', exact=True)
        newer = page.get_by_role('button', name='Newer tasks', exact=True)
        expect(rows).to_have_count(50)
        for _ in range(5):
            older.click()
        expect(rows).to_have_count(1)
        expect(rows).to_contain_text('historical-000')
        expect(older).to_be_disabled()
        newer.click()
        expect(rows).to_have_count(50)
        held_page = []
        page_pattern = f'http://127.0.0.1:{self.port}/history/tasks?*'

        def hold_history_page(route):
            held_page.append((route, route.fetch()))
            page.evaluate('window.__HISTORY_PAGE_HELD=true')

        page.route(page_pattern, hold_history_page, times=1)
        older.click()
        page.wait_for_function('window.__HISTORY_PAGE_HELD===true')
        expect(rows.first).to_be_disabled()
        expect(page.get_by_role('heading', name='Task history', exact=True, level=2)).to_be_visible()
        with page.expect_event('requestfinished', predicate=lambda request: '/history/tasks?' in request.url):
            held_page[0][0].fulfill(response=held_page[0][1])
        expect(rows).to_have_count(1)
        expect(rows).to_contain_text('historical-000')
        rows.first.click()
        expect(page.locator('.messages')).to_contain_text('ARCHIVED-CONVERSATION')
        selector = page.get_by_label('Activity task', exact=True)
        expect(selector).to_have_value(self.history_tasks[0])
        expect(page.locator('.activity-status p')).to_contain_text('historical-000')
        page.evaluate('window.__CLOSED_SOCKET=window.__UI_SOCKET; window.__UI_SOCKET.close()')
        page.wait_for_function('window.__UI_SOCKET !== window.__CLOSED_SOCKET && window.__UI_SOCKET.readyState === 1')
        expect(page.locator('.local-status')).to_contain_text('Connected locally')
        expect(selector).to_have_value(self.history_tasks[0])

        page.locator('.new-chat').click()
        expect(page.locator('.conversation-row.selected')).to_contain_text('New conversation')
        page.get_by_role('combobox', name='Tool access').select_option('coding')
        for cancel in (False, True):
            page.get_by_role('button', name='Agent', exact=True).click()
            self.scoped_plan_gate.clear()
            try:
                page.get_by_role('textbox', name='Message', exact=True).fill('Create the reviewed artifact')
                page.get_by_title('Send message', exact=True).click()
                expect(page.get_by_title('Cancel current task', exact=True)).to_be_visible()
                current = next(row for row in self.http('/activity')['tasks'] if row['status'] == 'running')
                # Controlled historical timestamp fixture: owned activity must survive head-page exclusion.
                with self.store.connection() as db:
                    db.execute('UPDATE tasks SET created=0 WHERE id=?', (current['id'],))
                page.evaluate('window.__CLOSED_SOCKET=window.__UI_SOCKET; window.__UI_SOCKET.close()')
                page.wait_for_function('window.__UI_SOCKET !== window.__CLOSED_SOCKET && window.__UI_SOCKET.readyState === 1')
                activity = self.http('/activity')
                self.assertEqual(len(activity['tasks']), 51)
                self.assertIn(current['id'], {row['id'] for row in activity['tasks']})
                page.get_by_role('button', name='Task history', exact=True).click()
                expect(rows).to_have_count(50)
                older.click()
                expect(rows.first).to_contain_text('historical-200')
                before = rows.all_text_contents()
                expect(page.get_by_role('button', name='Emergency stop', exact=True)).to_be_enabled()
            finally:
                self.scoped_plan_gate.set()
            approval = page.get_by_role('dialog', name='Review this action', exact=True)
            expect(approval).to_contain_text('create file', timeout=20000)
            self.assertFalse((self.policy.root / 'artifact.txt').exists())
            if cancel:
                approval.get_by_role('button', name='Emergency stop', exact=True).click()
            else:
                page.keyboard.press('Escape')
            expect(approval).to_have_count(0)
            expected_status = 'cancelled' if cancel else 'blocked'
            deadline = time.monotonic() + 15
            while self.http(f"/history/tasks/{current['id']}")['status'] != expected_status and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            expect(page.get_by_role('button', name='Emergency stop', exact=True)).to_be_enabled()
            self.assertEqual(rows.all_text_contents(), before)
            self.assertEqual(self.http(f"/history/tasks/{current['id']}")['status'], 'cancelled' if cancel else 'blocked')
            self.assertFalse((self.policy.root / 'artifact.txt').exists())
            page.get_by_role('button', name='Agent', exact=True).click()
            expect(selector).to_have_value(current['id'])
            expect(selector.locator('option:checked')).to_contain_text('cancelled' if cancel else 'blocked')
        held = []

        def delayed_metadata(route):
            held.append(route)
            page.evaluate('window.__TASK_META_HELD = true')

        pattern = f"**/history/tasks/{current['id']}"
        page.route(pattern, delayed_metadata)
        page.evaluate('window.__CLOSED_SOCKET=window.__UI_SOCKET; window.__UI_SOCKET.close()')
        page.wait_for_function('window.__TASK_META_HELD === true')
        page.get_by_role('button', name='Delete New conversation', exact=True).click()
        page.get_by_role('dialog').get_by_role('button', name='Delete conversation', exact=True).click()
        expect(page.get_by_role('dialog')).to_have_count(0)
        expect(page.locator('.conversation-row.selected')).to_have_count(0)
        with page.expect_event('requestfinished', predicate=lambda request: urlsplit(request.url).path == f"/history/tasks/{current['id']}"):
            response = held[0].fetch()  # Actual post-deletion404; a stale lookup must not become a current error.
            self.assertEqual(response.status, 404)
            held[0].fulfill(response=response)
        page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        page.unroute(pattern, delayed_metadata)
        expect(page.get_by_role('alert').filter(has_text='Resource not found')).to_have_count(0)
        expect(selector).to_have_value('')
        self.assertFalse(any(urlsplit(url).path == '/tasks' for url in requests), requests)
        self.assertNotIn('PRIVATE-HISTORY-RESULT', page.locator('body').inner_text())

    def run_message_scenario(self, page, requests):
        from urllib.parse import urlsplit

        from playwright.sync_api import expect

        page.get_by_role('button', name='Message pages', exact=True).click()
        rows = page.locator('.messages .message')
        older = page.get_by_role('button', name='Older messages', exact=True)
        newer = page.get_by_role('button', name='Newer messages', exact=True)
        latest = page.get_by_role('button', name='Latest messages', exact=True)
        expect(rows).to_have_count(50)
        expect(rows.first).to_contain_text('PAGE-MESSAGE-075')
        expect(rows.last).to_contain_text('PAGE-MESSAGE-124')
        expect(newer).to_be_disabled()
        older.click()
        expect(rows.first).to_contain_text('PAGE-MESSAGE-025')
        older.click()
        expect(rows).to_have_count(25)
        expect(rows.first).to_contain_text('PAGE-MESSAGE-000')
        expect(older).to_be_disabled()
        newer.click()
        expect(rows).to_have_count(50)
        expect(rows.first).to_contain_text('PAGE-MESSAGE-025')
        before = rows.all_text_contents()
        page.evaluate('window.__CLOSED_SOCKET=window.__UI_SOCKET; window.__UI_SOCKET.close()')
        page.wait_for_function('window.__UI_SOCKET !== window.__CLOSED_SOCKET && window.__UI_SOCKET.readyState === 1')
        expect(page.locator('.local-status')).to_contain_text('Connected locally')
        self.assertEqual(rows.all_text_contents(), before)
        latest.click()
        expect(rows.first).to_contain_text('PAGE-MESSAGE-075')
        page.get_by_role('button', name='Models & settings', exact=True).click()
        page.get_by_role('combobox', name='Context window', exact=True).select_option('16384')
        page.get_by_role('button', name='Agent', exact=True).click()
        page.get_by_role('combobox', name='Tool access').select_option('coding')
        self.scoped_plan_gate.clear()
        try:
            page.get_by_role('textbox', name='Message', exact=True).fill('Create the reviewed artifact')
            page.get_by_title('Send message', exact=True).click()
            expect(rows.last).to_contain_text('Create the reviewed artifact')
            older.click()
            expect(rows.first).to_contain_text('PAGE-MESSAGE-026')
            before = rows.all_text_contents()
        finally:
            self.scoped_plan_gate.set()
        approval = page.get_by_role('dialog', name='Review this action', exact=True)
        expect(approval).to_contain_text('create file', timeout=20000)
        page.keyboard.press('Escape')
        expect(approval).to_have_count(0)
        expect(page.locator('.activity-status strong')).to_have_text('Ready', timeout=15000)
        self.assertEqual(rows.all_text_contents(), before)
        self.assertFalse((self.policy.root / 'artifact.txt').exists())
        latest.click()
        expect(rows.last).to_contain_text('Approval denied: create_file', timeout=15000)
        older.click()
        expect(rows).to_have_count(50)
        with page.expect_download() as exported:
            page.get_by_role('button', name='Export', exact=True).click()
        content = Path(exported.value.path()).read_text(encoding='utf-8')
        self.assertIn('PAGE-MESSAGE-000', content)
        self.assertIn('PAGE-MESSAGE-124', content)
        self.assertIn('Approval denied: create_file', content)
        self.assertIn('Attachment: old.txt (1 KiB)', content)
        self.assertNotIn('EXPORT-ATTACHMENT-BYTES', content)
        self.assertNotIn('WEBSOCKET-PRIVATE-CANARY', content)
        self.assertNotIn('FOREIGN-MESSAGE-CANARY', content)
        expect(page.get_by_role('alert')).to_contain_text('Exported 127 messages')
        held = []

        def delayed_page(route):
            held.append((route, route.fetch()))
            page.evaluate('window.__MESSAGE_HELD = true')

        pattern = f'**/history/conversations/{self.message_chat}/messages?**'
        page.route(pattern, delayed_page)
        older.click()
        page.wait_for_function('window.__MESSAGE_HELD === true')
        with page.expect_event('requestfinished', predicate=lambda request: f'/{self.message_chat}/messages?' in request.url):
            try:
                page.get_by_role('button', name='WEBSOCKET-PRIVATE-CANARY', exact=True).click()
                expect(page.locator('.messages')).to_contain_text('FOREIGN-MESSAGE-CANARY')
            finally:
                held[0][0].fulfill(response=held[0][1])
        page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        expect(page.locator('.messages')).not_to_contain_text('PAGE-MESSAGE-')
        expect(page.locator('.messages')).to_contain_text('FOREIGN-MESSAGE-CANARY')
        page.unroute(pattern, delayed_page)
        page.get_by_role('button', name='Message pages', exact=True).click()
        expect(rows).to_have_count(50)
        downloads = []
        page.on('download', lambda download: downloads.append(download))
        with self.store.connection() as db:
            db.executemany('INSERT INTO messages(id,conversation,role,content,created) VALUES (?,?,?,?,?)',
                           [(f'limit-{i}', self.message_chat, 'user', 'export cap', 9999999999 + i) for i in range(5000)])
        page.get_by_role('button', name='Export', exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('5,000-message limit; no partial export')
        self.assertEqual(downloads, [])
        self.assertTrue(any('/messages?limit=50' in url for url in requests))
        self.assertFalse(any(urlsplit(url).path == f'/conversations/{self.message_chat}/messages' for url in requests))

    def run_conversation_scenario(self, page, requests):
        from urllib.parse import parse_qs, urlsplit

        from playwright.sync_api import expect

        rows = page.locator('.conversation-row')
        search = page.get_by_role('textbox', name='Search conversations', exact=True)
        older = page.get_by_role('button', name='Older conversations', exact=True)
        expect(rows).to_have_count(50)
        expect(page.get_by_role('button', name='History chat 00', exact=True)).to_have_count(0)
        older.click()
        expect(rows).to_have_count(72)
        expect(older).to_have_count(0)
        page.get_by_role('button', name='History chat 00', exact=True).click()
        expect(page.locator('.messages')).to_contain_text('OLDEST-TRANSCRIPT-CANARY')
        search.fill('History chat 01')
        expect(rows).to_have_count(1)
        expect(rows).to_contain_text('History chat 01')
        search.fill('')
        # The selected old chat stays pinned even though outside the newest50.
        expect(rows).to_have_count(51)
        expect(page.locator('.conversation-row.selected')).to_contain_text('History chat 00')
        expect(page.locator('.messages')).to_contain_text('OLDEST-TRANSCRIPT-CANARY')
        held = []

        def delay_old_search(route):
            query = parse_qs(urlsplit(route.request.url).query).get('query', [''])[0]
            if query == 'History chat 02':
                response = route.fetch()  # Actual authenticated backend response; only delay delivery.
                held.append((route, response))
                page.evaluate('window.__HISTORY_HELD = true')
            else:
                route.continue_()

        page.route('**/history/conversations?**', delay_old_search)
        search.fill('History chat 02')
        page.wait_for_function('window.__HISTORY_HELD === true')
        search.fill('History chat 03')
        expect(rows).to_have_count(1)
        expect(rows).to_contain_text('History chat 03')
        with page.expect_response(lambda response: 'query=History+chat+02' in response.url):
            held[0][0].fulfill(response=held[0][1])
        expect(rows).to_have_count(1)
        expect(rows).to_contain_text('History chat 03')
        page.unroute('**/history/conversations?**', delay_old_search)
        search.fill('not-a-title')
        expect(rows).to_have_count(0)
        expect(page.get_by_text('No conversations match.', exact=True)).to_be_visible()
        search.fill('')
        expect(rows).to_have_count(51)
        page.get_by_role('button', name='Rename History chat 00', exact=True).click()
        page.get_by_role('textbox', name='Conversation name', exact=True).fill('Renamed old conversation')
        page.get_by_role('button', name='Save name', exact=True).click()
        expect(page.locator('.conversation-row.selected')).to_contain_text('Renamed old conversation')
        expect(page.locator('.messages')).to_contain_text('OLDEST-TRANSCRIPT-CANARY')
        page.locator('.new-chat').click()
        expect(page.locator('.conversation-row.selected')).to_contain_text('New conversation')
        expect(page.locator('.messages')).not_to_contain_text('OLDEST-TRANSCRIPT-CANARY')
        expect(rows).to_have_count(50)
        page.get_by_role('button', name='Delete New conversation', exact=True).click()
        page.get_by_role('dialog').get_by_role('button', name='Delete conversation', exact=True).click()
        expect(page.get_by_role('button', name='New conversation', exact=True)).to_have_count(1)
        expect(page.locator('.conversation-row.selected')).to_have_count(0)
        with self.store.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM conversations').fetchone()[0], 72)
            self.assertEqual(db.execute("SELECT title FROM conversations WHERE id='history-chat-0'")
                             .fetchone()[0], 'Renamed old conversation')
        page.reload()
        expect(rows).to_have_count(50)
        self.assertFalse(self.inference_requests)
        self.assertTrue(any('/history/conversations?' in url for url in requests))
        self.assertFalse(any(urlsplit(url).path == '/conversations' for url in requests), requests)
        self.assertTrue(all(parse_qs(urlsplit(url).query).get('limit') == ['50']
                            for url in requests if urlsplit(url).path == '/history/conversations'))

    def run_accessibility_scenario(self, page):
        """Real browser keyboard/inertness and API actions; no synthetic focus trap."""
        from playwright.sync_api import expect

        page.set_viewport_size({'width': 900, 'height': 800})
        dialog = page.get_by_role('dialog')

        def contained_tabbing():
            for key in ('Tab',) * 10 + ('Shift+Tab',) * 10:
                page.keyboard.press(key)
                self.assertTrue(page.evaluate(
                    "document.activeElement.closest('dialog')?.matches(':modal') === true"))
            # A background control cannot steal focus while showModal is active.
            page.evaluate("document.querySelector('.new-chat').focus()")
            self.assertTrue(page.evaluate("document.activeElement.closest('dialog')?.matches(':modal') === true"))

        help_button = page.get_by_role('button', name='Slash commands', exact=True)
        help_button.focus()
        page.keyboard.press('Enter')
        expect(dialog).to_contain_text('Type / to browse commands')
        contained_tabbing()
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(help_button).to_be_focused()

        # Escape must not rename/delete or capture the user's screen.
        chat = page.locator('.conversation-row').first
        for action in ('Rename', 'Delete'):
            opener = chat.get_by_role('button', name=re.compile('^' + action + ' '))
            opener.focus()
            page.keyboard.press('Enter')
            expect(dialog).to_be_visible()
            contained_tabbing()
            page.keyboard.press('Escape')
            expect(dialog).to_have_count(0)
            expect(opener).to_be_focused()
        capture = page.get_by_role('button', name='Capture screenshot', exact=True)
        capture.click()
        expect(dialog).to_contain_text('Capture your main screen?')
        page.keyboard.press('Escape')
        expect(capture).to_be_focused()
        self.assertEqual(len(self.http('/tasks')['tasks']), 1)

        page.locator('input[type=file]').set_input_files({
            'name': 'keyboard.txt', 'mimeType': 'text/plain', 'buffer': b'KEYBOARD-PREVIEW'})
        preview = page.get_by_title('Preview keyboard.txt', exact=True)
        preview.click()
        expect(dialog).to_contain_text('KEYBOARD-PREVIEW')
        contained_tabbing()
        page.keyboard.press('Escape')
        expect(preview).to_be_focused()
        page.get_by_title('Remove keyboard.txt', exact=True).click()

        page.get_by_role('button', name='Project memory', exact=True).click()
        page.get_by_label('Memory note', exact=True).fill('KEYBOARD-MEMORY')
        page.get_by_role('button', name='Remember', exact=True).click()
        forget = page.get_by_role('button', name='Forget', exact=True)
        forget.click()
        expect(dialog).to_contain_text('Forget this memory?')
        contained_tabbing()
        page.keyboard.press('Escape')
        expect(forget).to_be_focused()
        self.assertEqual(len(self.http('/memory')), 1)

        activity = page.get_by_role('button', name='Activity', exact=True)
        activity.focus()
        page.keyboard.press('Enter')
        expect(dialog).to_contain_text('Agent activity')
        contained_tabbing()
        self.assertLessEqual(dialog.bounding_box()['x'] + dialog.bounding_box()['width'], 900)
        page.keyboard.press('Escape')
        expect(activity).to_be_focused()
        activity.click()
        page.set_viewport_size({'width': 1440, 'height': 1000})
        expect(dialog).to_have_count(0)
        page.get_by_role('button', name='Agent', exact=True).click()
        expect(page.locator('.activity-panel')).to_be_visible()
        page.set_viewport_size({'width': 900, 'height': 800})
        expect(page.locator('.activity-panel')).to_have_count(0)

        profile = page.get_by_role('combobox', name='Tool access')
        profile.select_option('coding')
        composer = page.get_by_role('textbox', name='Message', exact=True)
        self.scoped_plan_gate.clear()
        try:
            composer.fill('Create the reviewed artifact')
            page.get_by_title('Send message', exact=True).click()
            activity.click()
            expect(dialog).to_contain_text('Agent activity')
        finally:
            self.scoped_plan_gate.set()
        # The arriving approval is the top modal over the existing activity drawer.
        approval = page.get_by_role('dialog', name='Review this action', exact=True)
        expect(approval).to_contain_text('create file', timeout=20000)
        expect(approval.get_by_role('button', name='Deny', exact=True)).to_be_focused()
        contained_tabbing()
        page.keyboard.press('Escape')
        expect(approval).to_have_count(0)
        expect(dialog).to_contain_text('Agent activity')
        expect(page.locator('.activity-status strong')).to_have_text('Ready', timeout=15000)
        self.assertFalse((self.policy.root / 'artifact.txt').exists())
        self.assertEqual(self.http('/tasks')['approvals'], [])
        page.keyboard.press('Escape')
        expect(activity).to_be_focused()

        # A new conversation starts a fresh request; keyboard approval remains explicit.
        chat_count = page.locator('.conversation-row').count()
        page.locator('.new-chat').click()
        expect(page.locator('.conversation-row')).to_have_count(chat_count + 1)
        expect(page.locator('.conversation-row.selected .conversation')).to_have_text('New conversation')
        composer.fill('Create the reviewed artifact')
        page.get_by_title('Send message', exact=True).click()
        expect(approval).to_contain_text('create file', timeout=20000)
        approve = approval.get_by_role('button', name='Approve action', exact=True)
        approve.focus()
        page.keyboard.press('Enter')
        expect(approval).to_have_count(0)
        expect(page.locator('.message.assistant').last).to_contain_text('Fixture write completed', timeout=15000)
        self.assertEqual((self.policy.root / 'artifact.txt').read_text(), 'reviewed fixture')
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 900)

        chat_count = page.locator('.conversation-row').count()
        page.locator('.new-chat').click()
        expect(page.locator('.conversation-row')).to_have_count(chat_count + 1)
        expect(page.locator('.conversation-row.selected .conversation')).to_have_text('New conversation')
        composer.fill('Stop before new artifact')
        page.get_by_title('Send message', exact=True).click()
        expect(approval).to_contain_text('stopped-artifact.txt', timeout=20000)
        stop = approval.get_by_role('button', name='Emergency stop', exact=True)
        stop.focus()
        page.keyboard.press('Enter')
        expect(approval).to_have_count(0)
        expect(page.locator('.message.assistant').last).to_contain_text('Cancelled', timeout=15000)
        self.assertEqual(self.http('/tasks')['approvals'], [])
        self.assertTrue(any(task['status'] == 'cancelled' for task in self.http('/tasks')['tasks']))
        self.assertEqual((self.policy.root / 'artifact.txt').read_text(), 'reviewed fixture')
        self.assertFalse((self.policy.root / 'stopped-artifact.txt').exists())

    def run_scoped_scenario(self, page):
        """Actual browser PNG, worker approval and file write; only inference is a fixture."""
        import base64
        import io

        from PIL import Image
        from playwright.sync_api import expect

        page.get_by_role("button", name="Agent", exact=True).click()
        profile = page.get_by_role("combobox", name="Tool access")
        profile.select_option("browser")
        composer = page.get_by_role("textbox", name="Message", exact=True)
        composer.fill("Capture scoped browser preview")
        page.get_by_title("Send message", exact=True).click()
        expect(page.locator(".message.assistant .message-body").last).to_contain_text("SCOPED-A-RESULT", timeout=30000)
        task_a = next(task for task in self.http('/tasks')['tasks'] if task['id'] != self.task)
        result = task_a['result'] if isinstance(task_a['result'], dict) else json.loads(task_a['result'])
        self.assertEqual(result['status'], 'reported')
        self.assertEqual([step['tool'] for step in result['evidence']], ['browser_open', 'browser_screenshot'])
        self.assertTrue(all(step['ok'] for step in result['evidence']), result)
        opened = next(event['payload']['result']['untrusted_data'] for event in self.store.events()
                      if event['kind'] == 'tool_result' and event['payload'].get('name') == 'browser_open')
        self.assertEqual(opened['url'], self.scoped_site.url + '/')
        self.assertEqual(opened['title'], 'Agent fixture')
        self.assertIn('Local Agent Test', opened['text'])
        chat_a = task_a['conversation']
        page.get_by_role("button", name="Browser", exact=True).click()
        preview = page.locator('.preview-panel img')
        expect(preview).to_be_visible()
        image = preview.get_attribute('src')
        with Image.open(io.BytesIO(base64.b64decode(image.split(',', 1)[1]))) as observed:
            self.assertEqual(observed.format, 'PNG')
            self.assertGreater(observed.width, 100)
        self.assertEqual(page.get_by_label('Activity task').input_value(), task_a['id'])
        expect(page.locator('.activity-status strong')).to_have_text('Ready')
        expect(page.get_by_label('Activity task').locator(f"option[value='{task_a['id']}']")).to_contain_text('reported')
        expect(page.locator('.event-list')).to_contain_text('SCOPED-A-RESULT')
        # Production SQLite stores only a transient placeholder, not screenshot pixels.
        previews = [event for event in self.store.events() if event['kind'] == 'preview']
        self.assertTrue(previews)
        self.assertTrue(all(event['payload'] == {'transient': True} for event in previews))

        page.get_by_role("button", name="Agent", exact=True).click()
        profile.select_option('coding')
        self.scoped_plan_gate.clear()
        try:
            composer.fill('Create second scoped artifact')
            page.get_by_title("Send message", exact=True).click()
            # Switch before planning returns, proving global approvals are not hidden by selection.
            page.locator('.new-chat').click()
            expect(page.locator('.messages')).not_to_contain_text('SCOPED-A-RESULT')
            expect(page.locator('.event-list .event')).to_have_count(0)
            expect(page.locator('.activity-status strong')).to_have_text('Ready')
        finally:
            self.scoped_plan_gate.set()
        expect(page.get_by_role('dialog')).to_contain_text('create file', timeout=20000)
        expect(page.get_by_role('dialog')).to_contain_text('Source: Capture scoped browser preview')
        self.assertFalse((self.policy.root / 'artifact.txt').exists())
        expect(page.locator('.activity-status strong')).to_have_text('Ready')
        page.get_by_role('button', name='Open approval conversation', exact=True).click()
        task_b = next(task for task in self.http('/tasks')['tasks'] if task['status'] == 'waiting')
        self.assertEqual(task_b['conversation'], chat_a)
        self.assertEqual(page.get_by_label('Activity task').input_value(), task_b['id'])
        page.get_by_role('button', name='Approve action', exact=True).click()
        expect(page.get_by_role('dialog')).to_contain_text('execute code', timeout=15000)
        page.get_by_role('button', name='Approve action', exact=True).click()
        expect(page.locator('.message.assistant .message-body').last).to_contain_text('Fixture write completed', timeout=15000)
        self.assertEqual((self.policy.root / 'artifact.txt').read_text(), 'reviewed fixture')
        expect(page.locator('.command-output')).to_contain_text('Ran 1 test')
        page.get_by_role('button', name='Browser', exact=True).click()
        expect(preview).to_have_count(0)
        expect(page.locator('.event-list')).not_to_contain_text('SCOPED-A-RESULT')
        page.get_by_label('Activity task').select_option(task_a['id'])
        expect(preview).to_be_visible()
        self.assertEqual(preview.get_attribute('src'), image)
        expect(page.locator('.event-list')).to_contain_text('SCOPED-A-RESULT')
        expect(page.locator('.command-output')).to_have_count(0)
        page.get_by_label('Activity task').select_option(task_b['id'])
        expect(preview).to_have_count(0)
        expect(page.locator('.command-output')).to_contain_text('Ran 1 test')
        page.locator('.new-chat').click()
        expect(page.locator('.event-list .event')).to_have_count(0)
        expect(preview).to_have_count(0)
        expect(page.locator('.command-output')).to_have_count(0)
        # Reload/replay never reconstructs private screenshot pixels from retained history.
        page.reload()
        expect(page.locator('.local-status')).to_contain_text('Connected locally', timeout=15000)
        page.get_by_role('button', name='Capture scoped browser preview', exact=True).click()
        page.get_by_role('button', name='Browser', exact=True).click()
        page.get_by_label('Activity task').select_option(task_a['id'])
        expect(preview).to_have_count(0)
        expect(page.locator('.event-list')).to_contain_text('SCOPED-A-RESULT')
