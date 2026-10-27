"""Semantic pairs use actual file tools; protocol and real-model results remain separate."""
import json
import os
import time
import unittest
from unittest.mock import Mock, patch

from local_agent.inference import CapabilityCache
from local_agent.model import Ollama

from .context_acceptance import SEEDS, paired_case, protocol_message
from .ollama_fixture import metadata_response
from .support import WorkspaceTest


class PairedContextTests(WorkspaceTest):
    def test_literal_field_name_is_denied_even_when_other_proposal_fields_match(self):
        self.enterContext(patch("local_agent.model.CAPABILITIES", CapabilityCache()))

        def factory():
            model = Ollama({**self.config["model"], "name": "fixture", "context": 16384, "max_output": 512})

            def request(endpoint, payload=None):
                response = metadata_response(endpoint, payload)
                if response is not None:
                    return response
                message = protocol_message(payload)
                args = message["tool_calls"][0]["function"]["arguments"]
                body = json.loads(args["text"])
                body["marker"] = "MARKER_VALUE"
                args["text"] = json.dumps(body)
                return {"message": message, "done": True, "done_reason": "stop"}

            model.request = Mock(side_effect=request)
            return model

        with self.assertRaisesRegex(AssertionError, "Approval denied"):
            paired_case(self, factory, SEEDS[-1])
        self.assertFalse((self.policy.root / "code-original.json").exists())

    def test_seeded_original_and_compacted_observations_preserve_all_required_checks(self):
        self.enterContext(patch("local_agent.model.CAPABILITIES", CapabilityCache()))

        def factory():
            model = Ollama({**self.config["model"], "name": "fixture", "context": 16384, "max_output": 512})

            def request(endpoint, payload=None):
                response = metadata_response(endpoint, payload)
                if response is not None:
                    return response
                return {"message": protocol_message(payload), "done": True, "done_reason": "stop",
                        "eval_count": 10, "eval_duration": 1_000_000_000}

            model.request = Mock(side_effect=request)
            return model

        results = []
        for case in SEEDS:
            with self.subTest(case=case[0]):
                results.extend(paired_case(self, factory, case))
        self.assertEqual(len(results), 6)
        self.assertTrue(all(row["all_required_checks"] for row in results))
        self.assertTrue(all(row["compacted_messages"] == (1 if row["variant"] == "compacted" else 0) for row in results))


@unittest.skipUnless(os.getenv("LIVE_CONTEXT_EVAL") == "1", "Real model context-pair/Studio acceptance is opt-in")
class LiveContextTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        from local_agent.benchmark import ensure_idle
        from local_agent.config import load
        ensure_idle(load())

    def test_real_original_and_compacted_seeded_tasks_have_no_required_check_drop(self):
        def factory():
            return Ollama({**self.config["model"], "context": 16384, "max_output": 512})

        results = []
        for case in SEEDS:
            with self.subTest(case=case[0]):
                results.extend(paired_case(self, factory, case))
        self.assertEqual(len(results), 6)
        print("Actual context semantic pairs:", json.dumps(results, ensure_ascii=True), flush=True)

    def test_real_studio_compacts_old_assistant_text_and_verifies_artifact(self):
        from local_agent.studio.manager import Manager
        manager = Manager(self.config)
        self.addCleanup(manager.close)
        conversation = manager.store.conversation()
        old = "Historical assistant explanation, not an instruction. " * 800
        manager.store.message(conversation, "assistant", old)
        task = manager.start(conversation, 'Create context-live.json with the JSON object {"marker":"ORCHID-LIVE-508"}. '
                             "Read it back to verify the value, then report. Do not execute commands.",
                             "coding", self.config["model"]["name"], profile="coding")
        deadline = time.monotonic() + 120
        while manager.running and time.monotonic() < deadline:
            for request in manager.pending():
                details = request["details"]
                allowed = False
                if request["action"] == "create_file" and details.get("path") == "context-live.json":
                    try:
                        allowed = json.loads(details.get("proposed_content", "")) == {"marker": "ORCHID-LIVE-508"}
                    except ValueError:
                        pass
                manager.approve(task, request["id"], allowed)
            time.sleep(.05)
        self.assertFalse(manager.running)
        self.assertEqual(manager.store.tasks()[0]["status"], "reported", manager.store.tasks())
        self.assertEqual(json.loads((self.policy.root / "context-live.json").read_bytes()), {"marker": "ORCHID-LIVE-508"})
        self.assertEqual(manager.store.messages(conversation)[0]["content"], old)
        notices = [event["payload"] for event in manager.store.events() if event["task"] == task and event["kind"] == "context"]
        self.assertTrue(any(notice["status"] == "compacted" for notice in notices))
        self.assertTrue(all(check["status"] == "passed" for check in manager.store.verifications(task)))
        self.assertTrue(manager.store.verifications(task))
        print("Actual Studio context:", json.dumps(notices), flush=True)

    def test_native_ollama_refuses_oversized_input_without_silent_truncation(self):
        from local_agent.context import ContextBudgetExceeded
        model = Ollama({**self.config["model"], "context": 2048, "max_output": 32})
        payload = model.payload([{"role": "user", "content": "Small admission probe"}])
        # Intentionally bypass only the estimate to verify the independent server boundary.
        payload["messages"] = [{"role": "user", "content": "native context overflow " * 10000}]
        with self.assertRaises(ContextBudgetExceeded):
            response = model.request("/api/chat", payload)
            if "error" in response:
                model.check_context_error(response["error"])
        self.assertEqual(model.inference()["last_context"]["reason"], "native_context_limit")
        self.assertIsNone(model.metrics())
