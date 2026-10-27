import json

from local_agent.benchmark import ensure_idle, summarize
from local_agent.studio.store import Store

from .support import WorkspaceTest


class BenchmarkTests(WorkspaceTest):
    def test_restored_generation_active_tasks_are_checked_instead_of_original_history(self):
        original = Store(self.policy.state / 'studio.sqlite3')
        original.conversation('Original history')
        current = Store(self.policy.state / 'restore-staging' / ('a' * 32) / 'studio.sqlite3')
        chat = current.conversation('Restored history')
        task = current.task(chat, 'agent', 'fixture')
        (self.policy.state / 'studio-current.json').write_text(json.dumps({
            'version': 1, 'generation': 'a' * 32, 'store_id': current.identity,
            'rollback': 'b' * 32, 'rollback_sha256': 'c' * 64}))
        with self.assertRaisesRegex(RuntimeError, 'active task'):
            ensure_idle(self.config)
        current.finish(task, 'reported', {})
        ensure_idle(self.config)

    def test_refuses_to_compete_with_active_studio_task(self):
        ensure_idle(self.config)
        store = Store(self.policy.state / "studio.sqlite3")
        conversation = store.conversation()
        task = store.task(conversation, "agent", "fixture")
        with self.assertRaisesRegex(RuntimeError, "active task"):
            ensure_idle(self.config)
        store.finish(task, "reported", {})
        ensure_idle(self.config)

    def test_quality_checks_and_speed_are_reported_separately(self):
        rows = [{"context": 8192, "case": "throughput", "tokens_per_second": speed,
                 "first_token_seconds": 0.2, "elapsed_seconds": 3, "passed": None}
                for speed in (50, 60, 55)]
        rows += [{"context": 8192, "case": "tool_contract", "passed": passed} for passed in (True, False)]
        result = summarize(rows)[0]
        self.assertEqual(result["median_tokens_per_second"], 55)
        self.assertEqual((result["passed"], result["scored"]), (1, 2))
