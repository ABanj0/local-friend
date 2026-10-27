import shutil
import subprocess
import threading
import unittest
from unittest.mock import patch

from local_agent.studio.commands import COMMANDS, parse_command
from local_agent.studio.store import Store

from . import studio_support as fixtures
from .ollama_fixture import metadata_response
from .support import WorkspaceTest


class CommandParsingTests(unittest.TestCase):
    def test_catalog_is_unique_and_arguments_are_literal(self):
        self.assertEqual(len(COMMANDS), len({c.name for c in COMMANDS}))
        command, argument = parse_command(" /PLAN  Write a counter\nthen review it ")
        self.assertEqual((command.name, argument), ("plan", "Write a counter\nthen review it"))
        self.assertEqual(parse_command('/test folder with spaces')[1], 'folder with spaces')
        for value in ("/not-a-command", "/", "plain instruction"):
            with self.assertRaises(ValueError):
                parse_command(value)


class GoalStoreTests(WorkspaceTest):
    def test_goal_progress_persists_and_completion_is_explicit(self):
        store = Store(self.policy.state / "goals.db")
        conversation = store.conversation()
        goal = store.create_goal(conversation, "Build and verify counter")
        with self.assertRaises(ValueError):
            store.create_goal(conversation, "replace without asking")
        with self.assertRaises(ValueError):
            store.finish_goal(conversation, "completed")
        store.set_goal_plan(goal["id"], ["Implement", "Test"])
        store.goal_step(conversation, 0, True)
        store.set_goal_plan(goal["id"], ["Do not replace user progress"])
        reopened = Store(store.path)
        self.assertEqual(reopened.current_goal(conversation)["steps"], [
            {"text":"Implement","done":True}, {"text":"Test","done":False}])
        with self.assertRaises(ValueError):
            store.finish_goal(conversation, "completed")
        store.goal_step(conversation, 1, True)
        self.assertEqual(store.current_goal(conversation)["status"], "active")
        store.finish_goal(conversation, "completed")
        self.assertEqual(store.current_goal(conversation)["status"], "completed")
        store.create_goal(conversation, "Second goal")
        store.finish_goal(conversation, "cancelled")
        store.delete_conversation(conversation)
        self.assertIsNone(store.current_goal(conversation))


@unittest.skipUnless(fixtures.HAS_API, "Desktop API dependencies not installed")
class SlashAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def slash(self, instruction, **extra):
        return self.client.post('/slash', headers=self.headers, json={
            'conversation':self.conversation, 'model':'fixture', 'objective':instruction, **extra})

    def setUp(self):
        super().setUp()
        self.manager=self.client.app.state.manager
        self.conversation=self.manager.store.conversation()

    def test_authentication_unknown_commands_and_paths(self):
        self.assertEqual(self.client.get('/commands').status_code, 401)
        self.assertEqual(self.client.post('/slash',json={'conversation':self.conversation,'model':'fixture','objective':'/test'}).status_code,401)
        self.assertEqual(len(self.client.get('/commands', headers=self.headers).json()), len(COMMANDS))
        self.assertEqual(self.slash('/unknown').status_code, 400)
        self.assertEqual(self.slash('/plan').status_code, 400)
        self.assertEqual(self.slash('/test ../escape').status_code, 403)
        self.assertEqual(self.manager.store.tasks(), [])

    def test_goal_lifecycle_and_plan_dispatch(self):
        with patch('local_agent.studio.api.Ollama.request', side_effect=metadata_response), \
                patch.object(self.manager,'start',return_value='task') as start:
            result=self.slash('/goal Build a counter')
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(start.call_args.args[2], 'plan')
            goal=self.manager.store.current_goal(self.conversation)
            self.assertEqual(start.call_args.args[-1], goal['id'])
            self.assertEqual(self.slash('/goal Different goal').status_code,400)
            self.manager.store.set_goal_plan(goal['id'],['Write code','Verify tests'])
            self.assertEqual(self.slash('/goal complete').status_code,400)
            self.assertEqual(self.slash('/goal done 1').status_code,200)
            self.assertEqual(self.slash('/goal undo 1').status_code,200)
            self.assertEqual(self.slash('/goal done 9').status_code,400)
            self.assertEqual(self.slash('/goal run').status_code,200)
            self.assertEqual(start.call_args.args[2],'agent')
            for index in (1,2):
                self.assertEqual(self.slash(f'/goal done {index}').status_code,200)
            self.assertEqual(self.slash('/goal complete').status_code,200)
            self.assertEqual(self.client.get(f'/conversations/{self.conversation}/goal',headers=self.headers).json()['goal']['status'],'completed')

    def test_all_task_commands_route_without_expanding_permissions(self):
        routes={'chat':'chat','agent':'agent','browser':'browser','desktop':'desktop','code':'coding','summarize':'chat','plan':'plan'}
        with patch('local_agent.studio.api.Ollama.request',side_effect=metadata_response), \
                patch.object(self.manager,'start',return_value='task') as start:
            for command,mode in routes.items():
                with self.subTest(command=command):
                    response=self.slash(f'/{command} Inspect the attached context only')
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(start.call_args.args[2],mode)
                    self.assertEqual(start.call_args.args[4],'.')
            goal=self.manager.store.create_goal(self.conversation,'Plan a release')
            self.assertEqual(self.slash('/goal plan').status_code,200)
            self.assertEqual(start.call_args.args[-1],goal['id'])
            self.manager.store.set_goal_plan(goal['id'],['Review'])
            self.assertEqual(self.slash('/goal plan').status_code,400)
            self.assertEqual(self.slash('/goal cancel').status_code,200)
            self.assertEqual(self.manager.store.current_goal(self.conversation)['status'],'cancelled')
            self.assertEqual(self.slash('/goal set Plan a different release').status_code,200)

    def test_goal_cannot_complete_or_cancel_an_active_goal_task(self):
        goal=self.manager.store.create_goal(self.conversation,'Read a file')
        self.manager.store.set_goal_plan(goal['id'],['Read'])
        self.manager.store.goal_step(self.conversation,0,True)
        self.manager.running['fixture']={'goal':goal['id'],'done':False}
        try:
            self.assertEqual(self.slash('/goal complete').status_code,400)
            self.assertEqual(self.slash('/goal cancel').status_code,400)
        finally:
            self.manager.running.clear()

    def test_goal_model_preflight_does_not_hold_the_stop_lock(self):
        def preflight(*args, **kwargs):
            acquired=[]

            def probe():
                if self.manager.lock.acquire(timeout=0.5):
                    acquired.append(True)
                    self.manager.lock.release()

            thread=threading.Thread(target=probe)
            thread.start()
            thread.join(1)
            self.assertEqual(acquired,[True], 'Model I/O must not block cancellation/approval locking')
            return metadata_response(*args, **kwargs)

        with patch('local_agent.studio.api.Ollama.request',side_effect=preflight), \
                patch.object(self.manager,'start',return_value='task'):
            self.assertEqual(self.slash('/goal Create a counter').status_code,200)


class SlashProcessTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def test_plan_is_tool_free_and_regeneration_stays_tool_free(self):
        self.manager.start(self.conversation,'Create a file and run tests','plan','fixture')
        self.wait_until(lambda:not self.manager.running)
        self.assertEqual(self.manager.store.tasks()[0]['status'],'planned')
        self.assertFalse((self.policy.root/'review.txt').exists())
        self.assertFalse(any(event['kind']=='tool_start' for event in self.manager.live_events))
        self.assertTrue(all('tools' not in request for request in self.requests))
        self.manager.start(self.conversation,'','agent','fixture',regenerate=True)
        self.wait_until(lambda:not self.manager.running)
        self.assertEqual(self.manager.store.tasks()[0]['mode'],'plan')
        self.assertEqual(self.manager.pending(),[])

    def test_goal_plan_is_persisted_without_executing_it(self):
        goal=self.manager.store.create_goal(self.conversation,'Create a reviewed file')
        self.manager.start(self.conversation,goal['objective'],'plan','fixture',goal_id=goal['id'])
        self.wait_until(lambda:not self.manager.running)
        current=self.manager.store.current_goal(self.conversation)
        self.assertTrue(current['steps'])
        self.assertFalse(current['steps'][0]['done'])
        self.assertEqual(current['status'],'active')
        self.assertFalse((self.policy.root/'review.txt').exists())

    def test_test_shortcut_requires_approval_and_uses_no_model(self):
        (self.policy.root/'test_sample.py').write_text('import unittest\nclass Sample(unittest.TestCase):\n def test_sum(self): self.assertEqual(2+3,5)\n')
        task=self.manager.start(self.conversation,'Run tests','test','fixture')
        self.wait_until(lambda:bool(self.manager.pending()))
        self.assertEqual(self.requests,[])
        request=self.manager.pending()[0]
        self.assertEqual(request['action'],'execute_code')
        self.manager.approve(task,request['id'],True)
        self.wait_until(lambda:not self.manager.running)
        self.assertEqual(self.manager.store.tasks()[0]['status'],'reported')
        self.assertIn('Ran 1 test',self.manager.store.messages(self.conversation)[-1]['content'])
        self.assertEqual(self.requests,[])

    def test_diff_shortcut_never_bypasses_git_review(self):
        git=shutil.which('git')
        if not git:
            self.skipTest('Git unavailable')
        subprocess.run([git,'init'],cwd=self.policy.root,check=True,capture_output=True)
        (self.policy.root/'sample.py').write_text('counter = 1\n')
        subprocess.run([git,'add','-N','--','sample.py'],cwd=self.policy.root,check=True,capture_output=True)
        task=self.manager.start(self.conversation,'Review diff','diff','fixture')
        self.wait_until(lambda:bool(self.manager.pending()))
        request=self.manager.pending()[0]
        self.assertEqual(request['action'],'git_diff')
        self.manager.approve(task,request['id'],True)
        self.wait_until(lambda:not self.manager.running)
        self.assertIn('+counter = 1',self.manager.store.messages(self.conversation)[-1]['content'])
        self.assertEqual(self.requests,[])
