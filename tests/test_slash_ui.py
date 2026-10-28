import os
import shutil
import sqlite3
import subprocess
import unittest
from pathlib import Path

from . import studio_ui_support as ui_fixtures
from .support import WorkspaceTest


@unittest.skipUnless(os.getenv("LIVE_STUDIO_UI") == "1", "Set LIVE_STUDIO_UI=1 after building the frontend")
class SlashUITests(ui_fixtures.StudioUIFixture, WorkspaceTest):
    def test_slash_commands_and_chat_attachment_management(self):
        self.run_chat_attachment_management()

    def additional_ui_checks(self, page):
        from playwright.sync_api import expect
        box=page.get_by_role('textbox',name='Message',exact=True)

        def send(command):
            box.fill(command)
            box.press('Enter')

        def ready():
            expect(page.locator('.activity-status strong')).to_have_text('Ready',timeout=120000)

        expect(page.get_by_role('button',name='Slash commands',exact=True)).to_be_visible()
        box.fill('/')
        expect(page.get_by_role('listbox',name='Slash commands')).to_be_visible()
        box.press('ArrowDown')
        box.press('Tab')
        expect(box).to_have_value('/plan ')
        box.fill('/')
        box.press('Escape')
        expect(page.get_by_role('listbox',name='Slash commands')).to_have_count(0)
        send('/help')
        expect(page.get_by_role('dialog')).to_contain_text('/goal')
        page.get_by_role('button',name='Close command help').click()
        send('/not-a-command')
        expect(page.get_by_role('alert')).to_contain_text('Unknown command')

        send('/plan Create counter.py, add tests, and run them. Produce a plan only.')
        expect(page.locator('.message.assistant').last).to_contain_text('Proposed plan',timeout=120000)
        ready()
        expect(page.locator('.event-kind.tool_start')).to_have_count(0)
        self.assertEqual(list((Path(self.temp.name)/'workspace').glob('*.py')),[])
        page.get_by_title('Regenerate the latest request',exact=True).click()
        expect(page.locator('.message.assistant')).to_have_count(2,timeout=120000)
        ready()
        expect(page.locator('.event-kind.tool_start')).to_have_count(0)

        send('/goal set Use only the files tool to list the workspace and report its file count. Do not create files or run commands.')
        expect(page.locator('.goal-panel ol li').first).to_be_visible(timeout=120000)
        ready()
        expect(page.get_by_role('button',name='Complete goal',exact=True)).to_be_disabled()
        send('/rename Slash acceptance')
        expect(page.locator('.conversation-row')).to_contain_text('Slash acceptance')
        send('/goal status')
        expect(page.get_by_role('alert')).to_contain_text('Goal (active)')
        page.get_by_role('button',name='Run goal',exact=True).click()
        expect(page.locator('.event-list')).to_contain_text('"name": "files"',timeout=120000)
        ready()
        expect(page.locator('.goal-panel input:checked')).to_have_count(0)
        page.reload()
        expect(page.locator('.local-status')).to_contain_text('Connected locally',timeout=15000)
        page.locator('.conversation').filter(has_text='Slash acceptance').click()
        expect(page.locator('.goal-panel')).to_contain_text('Use only the files tool')
        send('/goal done 1')
        expect(page.locator('.goal-panel input').first).to_be_checked()
        send('/goal undo 1')
        expect(page.locator('.goal-panel input').first).not_to_be_checked()
        for index in range(page.locator('.goal-panel input').count()):
            checkbox=page.locator('.goal-panel input').nth(index)
            checkbox.click()
            expect(checkbox).to_be_checked()
        page.get_by_role('button',name='Complete goal',exact=True).click()
        expect(page.locator('.goal-panel')).to_contain_text('Completed by you')
        send('/model')
        expect(page.get_by_role('heading',level=1)).to_have_text('Models & settings')
        page.get_by_role('navigation').get_by_role('button',name='Chat',exact=True).click()
        send('/model qwen3.5:9b')
        expect(page.get_by_role('alert')).to_contain_text('Active model: qwen3.5:9b')
        count=page.locator('.message.assistant').count()
        send('/chat Reply only SLASH-CHAT-OK.')
        expect(page.locator('.message.assistant')).to_have_count(count+1,timeout=120000)
        expect(page.locator('.message.assistant').last).to_contain_text('SLASH-CHAT-OK')
        ready()
        count=page.locator('.message.assistant').count()
        send('/summarize Focus on the tracked objective and what was actually inspected.')
        expect(page.locator('.message.assistant')).to_have_count(count+1,timeout=120000)
        ready()

        workspace=Path(self.temp.name)/'workspace'
        (workspace/'test_counter.py').write_text('import unittest\nclass TestCounter(unittest.TestCase):\n def test_increment(self): self.assertEqual(1+1,2)\n')
        send('/test')
        expect(page.get_by_role('dialog')).to_contain_text('execute code',timeout=15000)
        expect(page.locator('.chat-icon[title^="Delete"]').first).to_be_disabled()
        page.get_by_role('button',name='Deny',exact=True).click()
        expect(page.locator('.message.assistant').last).to_contain_text('not run',timeout=10000)
        ready()
        send('/test')
        expect(page.get_by_role('dialog')).to_contain_text('unittest',timeout=15000)
        page.get_by_role('button',name='Approve action',exact=True).click()
        expect(page.locator('.message.assistant').last).to_contain_text('Ran 1 test',timeout=15000)
        ready()
        send('/test')
        expect(page.get_by_role('dialog')).to_contain_text('execute code',timeout=15000)
        db = sqlite3.connect(Path(self.temp.name)/'.runtime/state/studio.sqlite3')
        try:
            db.execute('BEGIN IMMEDIATE')
            # Use this isolated app's authenticated API to cancel behind the approval modal.
            page.evaluate("""async () => {
                const c=await window.__TAURI_INTERNALS__.invoke('backend_connection');
                const base=`http://127.0.0.1:${c.port}`;
                const headers={Authorization:`Bearer ${c.token}`};
                const snapshot=await (await fetch(base+'/tasks',{headers})).json();
                const task=snapshot.tasks.find(t=>t.status==='waiting');
                const response=await fetch(base+`/tasks/${task.id}/cancel`,{method:'POST',headers});
                if(!response.ok)throw new Error('Fixture cancellation failed');
            }""")
            expect(page.locator('.activity-status strong')).to_have_text('Waiting for storage',timeout=10000)
            expect(page.get_by_role('alert')).to_contain_text('Worker stopped')
            expect(page.get_by_role('dialog')).to_have_count(0)
        finally:
            db.rollback()
            db.close()
        expect(page.locator('.message.assistant').last).to_contain_text('Cancelled',timeout=10000)
        ready()
        git=shutil.which('git')
        if git:
            subprocess.run([git,'init'],cwd=workspace,capture_output=True,check=True)
            subprocess.run([git,'add','-N','--','test_counter.py'],cwd=workspace,capture_output=True,check=True)
            send('/diff')
            expect(page.get_by_role('dialog')).to_contain_text('git diff',timeout=15000)
            page.get_by_role('button',name='Approve action',exact=True).click()
            expect(page.locator('.message.assistant').last).to_contain_text('+import unittest',timeout=15000)
            ready()

        send('/chat Explain Python arithmetic in detail with worked examples: operators, precedence, floating point, Decimal, fractions, and testing. Begin the explanation immediately.')
        expect(page.locator('.activity-status strong')).to_have_text('Working',timeout=10000)
        send('/stop')
        expect(page.locator('.message.assistant').last).to_contain_text('Cancelled',timeout=10000)
        ready()
        # Force /stop before the task-start POST reaches the server. It must be
        # queued, not silently discarded by the pending-submission guard.
        page.evaluate("""() => {
            window.__originalSlashFetch=window.fetch;
            window.fetch=async (resource,options) => {
                if(String(resource).endsWith('/slash') && JSON.parse(options.body).objective.startsWith('/chat'))
                    await new Promise(resolve=>setTimeout(resolve,1500));
                return window.__originalSlashFetch(resource,options);
            };
        }""")
        count=page.locator('.message.assistant').count()
        send('/chat Give a detailed explanation of arithmetic with many examples. Start immediately.')
        expect(page.get_by_title('Send message',exact=True)).to_be_disabled()
        send('/stop')
        expect(page.get_by_role('alert')).to_contain_text('Stop requested')
        expect(page.locator('.message.assistant')).to_have_count(count+1,timeout=15000)
        expect(page.locator('.message.assistant').last).to_contain_text('Cancelled')
        ready()
        page.evaluate('window.fetch=window.__originalSlashFetch')
        with page.expect_download() as download:
            send('/export')
        self.assertTrue(download.value.suggested_filename.endswith('.md'))
        page.screenshot(path=str(Path.cwd()/'workspace/studio-slash-goal-acceptance.png'))
        send('/new Fresh slash conversation')
        expect(page.locator('.conversation-row')).to_have_count(2)
        expect(page.locator('.goal-panel')).to_have_count(0)
        send('/delete')
        expect(page.get_by_role('dialog')).to_contain_text('cannot be undone')
        page.get_by_role('button',name='Cancel',exact=True).click()
        expect(page.locator('.conversation-row')).to_have_count(2)
        send('/delete')
        page.get_by_role('button',name='Delete conversation',exact=True).click()
        expect(page.locator('.conversation-row')).to_have_count(1)
        page.locator('.conversation').filter(has_text='Slash acceptance').click()
        send('/delete')
        page.get_by_role('button',name='Delete conversation',exact=True).click()
        expect(page.locator('.conversation-row')).to_have_count(0)
        page.get_by_role('navigation').get_by_role('button',name='Chat',exact=True).click()
