"""Option/admission tests use a real loopback protocol fixture, never model-quality claims."""
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from local_agent.inference import (
    PROBE_SCHEMA,
    CapabilityCache,
    InferenceIncomplete,
    InferenceOptions,
)
from local_agent.model import Ollama

from .ollama_fixture import metadata_response
from .studio_support import StudioAPIFixture, StudioProcessFixture
from .support import WorkspaceTest


class InferenceSite:
    def __init__(self):
        self.digest, self.version = "a" * 64, "0.40.7"
        self.name, self.reason = "fixture", "stop"
        self.capabilities = ["completion", "tools", "vision", "thinking"]
        self.thinking = {"values": [False, True], "default": True}
        self.schema_value = {"ok": True}
        self.remote, self.installed = False, True
        self.thinking_chunk = False
        self.requests = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def send(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode() + b"\n")

            def do_GET(self):
                fixture.requests.append((self.path, None))
                response = metadata_response(self.path, name=fixture.name, digest=fixture.digest)
                if self.path == "/api/version":
                    response = {"version": fixture.version}
                if self.path == "/api/tags" and not fixture.installed:
                    response = {"models": []}
                self.send(response)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fixture.requests.append((self.path, body))
                if self.path == "/api/show":
                    response = {"capabilities": fixture.capabilities, "thinking": fixture.thinking,
                                "details": {"format": "gguf"}}
                    if fixture.remote:
                        response["remote_model"] = "remote"
                    self.send(response)
                    return
                message = {"role": "assistant", "content": "Hello Unicode: 世界 🐍\nprint(1)"}
                probe = body.get("format") == PROBE_SCHEMA
                if probe:
                    message["content"] = json.dumps(fixture.schema_value)
                elif body.get("format"):
                    message["content"] = '{"steps":["Observe"]}'
                final = {"done": True, "done_reason": "stop" if probe else fixture.reason,
                         "message": message, "eval_count": 3, "eval_duration": 1_000_000_000,
                         "prompt_eval_count": 12, "load_duration": 20_000_000,
                         "prompt_eval_duration": 30_000_000, "total_duration": 1_050_000_000}
                if body.get("stream"):
                    self.send_response(200)
                    self.end_headers()
                    if fixture.thinking_chunk:
                        self.wfile.write(json.dumps({"message": {"thinking": "private reasoning"}}).encode() + b"\n")
                    self.wfile.write(json.dumps({"message": message}).encode() + b"\n")
                    final["message"] = {"role": "assistant", "content": ""}
                    self.wfile.write(json.dumps(final).encode() + b"\n")
                else:
                    self.send(final)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.site = InferenceSite()
        self.addCleanup(self.site.close)
        self.now = 0
        self.cache = CapabilityCache(ttl=10, clock=lambda: self.now)
        self.enterContext(patch("local_agent.model.CAPABILITIES", self.cache))
        self.config = {"url": self.site.url, "name": "fixture", "timeout": 3,
                       "context": 4096, "temperature": .3, "max_output": 517,
                       "thinking": True, "keep_alive": "60s"}

    def model(self, **changes):
        return Ollama({**self.config, **changes})

    def test_chat_plan_tool_and_stream_payloads_share_validated_settings(self):
        model = self.model()
        messages = [{"role": "user", "content": "世界 🐍\nprint(1)"}]
        model.chat(messages)
        model.chat(messages, schema={"type": "object"})
        model.chat(messages, tools=[{"type": "function", "function": {"name": "files", "parameters": {"type": "object"}}}])
        self.assertIn("世界", "".join(model.stream_chat(messages)))
        requests = [body for path, body in self.site.requests if path == "/api/chat" and body.get("format") != PROBE_SCHEMA]
        self.assertEqual(len(requests), 4)
        for body in requests:
            self.assertEqual(body["options"], {"num_ctx": 4096, "temperature": .3, "num_predict": 517})
            self.assertIs(body["think"], True)
            self.assertEqual(body["keep_alive"], "60s")
            self.assertEqual(body["messages"], messages)
        self.assertEqual(model.metrics()["model_calls"], 4)

    def test_native_timings_and_stream_first_content_are_observed_without_nonstream_guess(self):
        model = self.model()
        model.chat([])
        list(model.stream_chat([]))
        calls = model.inference()["calls"]
        self.assertEqual(calls[0]["prompt_tokens"], 12)
        self.assertEqual(calls[0]["load_ns"], 20_000_000)
        self.assertEqual(calls[0]["prompt_ns"], 30_000_000)
        self.assertIsNone(calls[0]["first_content_seconds"])
        self.assertIsNone(calls[0]["first_token_seconds"])
        self.assertGreaterEqual(calls[1]["first_content_seconds"], 0)
        self.assertEqual([c["finish_reason"] for c in calls], ["stop", "stop"])

    def test_first_thinking_token_is_timed_separately_without_exposing_reasoning(self):
        self.site.thinking_chunk = True
        model = self.model()
        text = "".join(model.stream_chat([]))
        call = model.inference()["calls"][0]
        self.assertLessEqual(call["first_token_seconds"], call["first_content_seconds"])
        self.assertNotIn("private reasoning", text + json.dumps(model.inference()))

    def test_tool_vision_and_completion_capabilities_fail_before_generation(self):
        for capability, arguments in (("tools", {"tools": True}), ("vision", {"vision": True}), ("completion", {})):
            with self.subTest(capability=capability):
                self.site.capabilities = [c for c in ["completion", "tools", "vision"] if c != capability]
                self.site.digest = (str(len(self.site.requests) % 10) * 64)
                with self.assertRaisesRegex(ValueError, capability):
                    self.model().admit(**arguments)
        self.assertFalse(any(path == "/api/chat" for path, _ in self.site.requests))

    def test_cache_reuses_show_but_rechecks_identity_version_expiry_and_deletion(self):
        model = self.model()
        model.admit()
        model.admit()
        shows = lambda: sum(path == "/api/show" for path, _ in self.site.requests)
        self.assertEqual(shows(), 1)
        self.site.digest = "b" * 64
        model.admit()
        self.assertEqual(shows(), 2)
        self.site.version = "0.40.8"
        model.admit()
        self.assertEqual(shows(), 3)
        self.now = 11
        model.admit()
        self.assertEqual(shows(), 4)
        self.site.installed = False
        with self.assertRaisesRegex(ValueError, "installed"):
            model.admit()

    def test_cache_is_separate_for_model_and_returns_copies(self):
        first = self.model().admit()
        first["capabilities"].clear()
        self.assertIn("tools", self.model().admit()["capabilities"])
        self.site.name = "other"
        self.model(name="other").admit()
        self.assertEqual(len(self.cache.items), 2)

    def test_local_metadata_rejects_remote_and_malformed_identities(self):
        self.site.remote = True
        with self.assertRaisesRegex(ValueError, "remote"):
            self.model().admit()
        self.site.remote = False
        for value in (None, "invalid", "B" * 64):
            self.site.digest = value
            with self.subTest(digest=value), self.assertRaisesRegex(ValueError, "identity"):
                self.model().admit()

    def test_named_thinking_controls_are_exact_and_model_default_is_explicit(self):
        self.site.thinking = {"values": ["low", "high"], "default": "low"}
        self.model(thinking="high").chat([])
        with self.assertRaisesRegex(ValueError, "thinking"):
            self.model(thinking=False).admit()
        with self.assertRaisesRegex(ValueError, "thinking"):
            self.model(thinking="medium").admit()
        self.model(thinking=None).chat([])
        bodies = [body for path, body in self.site.requests if path == "/api/chat"]
        self.assertEqual([b["think"] for b in bodies], ["high", None])

    def test_schema_probe_is_bounded_reused_and_incompatible_output_is_rejected(self):
        model = self.model()
        model.admit(schema=True)
        model.admit(schema=True)
        probes = [body for path, body in self.site.requests if path == "/api/chat"]
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0]["options"]["num_predict"], 64)
        self.assertFalse(probes[0].get("tools"))
        self.assertIsNone(model.metrics())
        self.site.digest = "b" * 64
        self.site.schema_value = {"ok": 1}
        with self.assertRaisesRegex(ValueError, "structured-output"):
            model.admit(schema=True)

    def test_length_and_unknown_finishes_are_not_returned_as_complete(self):
        for reason in ("length", "load", "unload", None, "arbitrary secret reason"):
            for stream in (True, False):
                self.site.reason = reason
                model = self.model()
                with self.subTest(reason=reason, stream=stream), self.assertRaises(InferenceIncomplete):
                    list(model.stream_chat([])) if stream else model.chat([])
                self.assertEqual(model.metrics()["generated_tokens"], 3)
                self.assertNotIn("arbitrary secret", json.dumps(model.inference()))

    def test_strict_options_reject_invalid_types_nonfinite_values_and_unbounded_residency(self):
        bad = {"context": [True, 2047, 32769, "4096"], "temperature": [True, float("nan"), float("inf"), -1, 3],
               "max_output": [True, 0, -1, 32769, "5"], "thinking": [1, {}, "HIGH", "a" * 33],
               "keep_alive": [True, -1, 3601, "-1", "forever", "61m", "5h"]}
        for field, values in bad.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    InferenceOptions.from_config({field: value})
        self.assertEqual(InferenceOptions.from_config({}).max_output, 2048)
        self.assertIsNone(InferenceOptions.from_config({"thinking": "default"}).thinking)

    def test_image_payload_is_preserved_and_unsupported_images_are_not_dropped(self):
        import base64

        from .test_vision import png
        messages = [{"role": "user", "content": "世界: describe image and code", "images": [base64.b64encode(png()).decode()]}]
        self.model().chat(messages)
        body = next(body for path, body in self.site.requests if path == "/api/chat")
        self.assertEqual(body["messages"], messages)
        self.site.digest = "b" * 64
        self.site.capabilities.remove("vision")
        before = sum(path == "/api/chat" for path, _ in self.site.requests)
        with self.assertRaisesRegex(ValueError, "vision"):
            self.model().chat(messages)
        self.assertEqual(sum(path == "/api/chat" for path, _ in self.site.requests), before)

    def test_malformed_metadata_fails_closed_with_no_generation(self):
        cases = {"/api/tags": [None, {"models": None}], "/api/version": [[], {"version": "secret"}],
                 "/api/show": [None, {"details": None}, {"details": {"format": "gguf"}, "capabilities": None},
                               {"details": {"format": "gguf"}, "capabilities": ["completion"], "thinking": None}]}
        for endpoint, values in cases.items():
            for value in values:
                with self.subTest(endpoint=endpoint, value=value):
                    self.cache.items.clear()
                    model = self.model()
                    request = model.request
                    def replacement(path, body=None, value=value, endpoint=endpoint, request=request):
                        return value if path == endpoint else request(path, body)
                    with patch.object(model, "request", side_effect=replacement), self.assertRaises(ValueError):
                        model.admit()
        self.assertFalse(any(path == "/api/chat" for path, _ in self.site.requests))

    def test_cache_and_timing_history_have_explicit_bounds(self):
        self.cache.limit = 2
        for name in ("one", "two", "three"):
            self.site.name = name
            self.model(name=name).admit()
        self.assertEqual(len(self.cache.items), 2)
        model = self.model()
        for _ in range(130):
            model.record_completion({"done": True, "done_reason": "stop"}, 0)
        self.assertEqual(len(model.inference()["calls"]), 128)
        self.assertEqual(model.inference()["omitted_calls"], 2)


class InferenceProcessTests(StudioProcessFixture, WorkspaceTest):
    def setUp(self):
        self.limited_stage = None
        self.finish_reason = lambda body: "length" if (
            self.limited_stage == "chat" and body.get("stream")
            or self.limited_stage == "plan" and body.get("format")
            or self.limited_stage == "tool" and body.get("tools")) else "stop"
        super().setUp()

    def test_all_studio_modes_receive_same_explicit_options(self):
        settings = {"context": 4096, "temperature": .3, "max_output": 517, "thinking": True, "keep_alive": "60s"}
        for mode in ("chat", "plan", "agent"):
            with self.subTest(mode=mode):
                self.requests.clear()
                task = self.manager.start(self.conversation, "世界: inspect print(1)", mode, "fixture", settings=settings)
                if mode == "agent":
                    self.wait_until(lambda: bool(self.manager.pending()))
                    self.manager.approve(task, self.manager.pending()[0]["id"], False)
                self.wait_until(lambda: not self.manager.running)
                self.assertTrue(self.requests)
                for body in self.requests:
                    self.assertEqual(body["options"], {"num_ctx": 4096, "temperature": .3, "num_predict": 517})
                    self.assertIs(body["think"], True)
                    self.assertEqual(body["keep_alive"], "60s")

    def test_internal_settings_cannot_override_endpoint_or_execution_limits(self):
        for settings in ({"url": "http://external.invalid"}, {"max_steps": 1000}, {"thinking": 1}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                self.manager.start(self.conversation, "Inspect", "agent", "fixture", settings=settings)
        self.assertEqual(self.manager.store.tasks(), [])
        self.assertFalse(self.requests)

    def test_truncated_stream_keeps_partial_text_and_cannot_report_success(self):
        self._run_truncation("chat")

    def _run_truncation(self, mode):
        self.limited_stage = mode
        task = self.manager.start(self.conversation, "Write a file", "agent" if mode == "tool" else mode, "fixture")
        self.wait_until(lambda: not self.manager.running)
        row = next(row for row in self.manager.store.tasks() if row["id"] == task)
        self.assertEqual(row["status"], "blocked", row)
        self.assertFalse((self.policy.root / "review.txt").exists())
        self.assertFalse(self.manager.pending())
        self.assertEqual(self.manager.store.journal(task)["operations"], [])
        message = self.manager.store.messages(self.conversation)[-1]
        self.assertIn("incomplete", message["content"].lower())
        if mode == "chat":
            self.assertIn("hello world", message["content"])
            self.assertEqual(message["metrics"]["inference"]["calls"][-1]["finish_reason"], "length")

    def test_truncated_plan_never_dispatches_a_tool(self):
        self._run_truncation("plan")

    def test_truncated_tool_call_is_never_dispatched(self):
        self._run_truncation("tool")


class InferenceAPITests(StudioAPIFixture, WorkspaceTest):
    def test_preferences_and_tasks_share_strict_validation(self):
        store = self.client.app.state.manager.store
        conversation = store.conversation()
        for changes in ({"thinking": 1}, {"max_output": True}, {"context": "4096"},
                        {"temperature": True}, {"keep_alive": -1}, {"keep_alive": "61m"}):
            for path in ("/tasks", "/preferences"):
                with self.subTest(path=path, changes=changes):
                    body = {"model": "fixture", "conversation": conversation, "objective": "Inspect", **changes}
                    self.assertEqual(self.client.post(path, headers=self.headers, json=body).status_code, 422)
        self.assertEqual(store.tasks(), [])

    def test_admission_is_authenticated_and_does_not_execute_generation(self):
        self.assertEqual(self.client.get("/models/capabilities?model=fixture").status_code, 401)
        with patch("local_agent.studio.api.Ollama.request", side_effect=metadata_response) as request:
            response = self.client.get("/models/capabilities?model=fixture", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["schema_probe"], "not_probed")
        self.assertFalse(any(call.args[0] == "/api/chat" for call in request.call_args_list))

    def test_options_persist_and_are_forwarded_without_expanding_tool_permissions(self):
        manager = self.client.app.state.manager
        conversation = manager.store.conversation()
        options = {"context": 4096, "temperature": .3, "max_output": 517, "thinking": None, "keep_alive": "60s"}
        self.assertEqual(self.client.post("/preferences", headers=self.headers, json={"model": "fixture", **options}).status_code, 200)
        saved = self.client.get("/preferences", headers=self.headers).json()
        self.assertTrue(all(saved[key] == value for key, value in options.items()))
        with patch("local_agent.studio.api.Ollama.request", side_effect=metadata_response), patch.object(manager, "start", return_value="task") as start:
            response = self.client.post("/tasks", headers=self.headers, json={"conversation": conversation,
                "objective": "Inspect", "model": "fixture", "mode": "coding", "profile": "coding", **options})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(start.call_args.args[5], options)
        self.assertEqual(start.call_args.kwargs["profile"], "coding")


class LiveInferenceTests(WorkspaceTest):
    @unittest.skipUnless(os.getenv("LOCAL_AGENT_MODEL_TEST") == "1", "Actual Ollama output-limit/timing acceptance is opt-in")
    def test_actual_model_enforces_configured_output_limit_and_reports_timing(self):
        from local_agent.benchmark import ensure_idle
        from local_agent.config import load
        ensure_idle(load())
        model = Ollama({**self.config["model"], "max_output": 1, "thinking": False})
        with self.assertRaises(InferenceIncomplete):
            list(model.stream_chat([{"role": "user", "content": "Write a long numbered list of 100 Python programming tips."}]))
        call = model.inference()["calls"][-1]
        self.assertEqual(call["finish_reason"], "length")
        self.assertIsNotNone(call["first_content_seconds"])
        self.assertIsNotNone(call["first_token_seconds"])
        self.assertIsNotNone(call["prompt_tokens"])
        self.assertIsNotNone(call["load_ns"])
        self.assertEqual(model.metrics()["generated_tokens"], 1)
        print("Actual-model limit/timing:", json.dumps(call), flush=True)
