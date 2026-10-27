import json
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .context import ContextBudgetExceeded, prepare, validate_notice
from .inference import (
    CAPABILITIES,
    PROBE_SCHEMA,
    InferenceIncomplete,
    InferenceOptions,
    supported_thinking,
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Ollama redirects are disabled to keep inference local")


class Ollama:
    def __init__(self, config):
        self.config = dict(config)
        self.usage = []
        self.inferences = []
        self.contexts = []
        self.probe_count, self.probe_seconds, self.omitted_calls = 0, 0, 0
        self.options = InferenceOptions.from_config(config)
        address = urlsplit(config["url"])
        if address.scheme != "http" or address.hostname not in {"127.0.0.1", "::1", "localhost"} or address.username or address.password or address.path not in {"", "/"}:
            raise ValueError("Inference endpoint must be a local HTTP Ollama server")
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def record_usage(self, response):
        # Only Ollama's final response contains authoritative token counts/timings.
        count, duration = response.get("eval_count"), response.get("eval_duration")
        if response.get("done") is True and type(count) is int and count >= 0 and type(duration) is int and duration >= 0:
            self.usage.append((count, duration))

    def metrics(self):
        if not self.usage:
            return None
        count = sum(item[0] for item in self.usage)
        duration = sum(item[1] for item in self.usage)
        return {"generated_tokens": count, "tokens_per_second": count * 1e9 / duration if duration else None,
                "model_calls": len(self.usage)}

    def request(self, endpoint, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(self.config["url"].rstrip("/") + endpoint, data=data,
                          headers={"Content-Type": "application/json"})
        timeout = min(self.config["timeout"], 5) if endpoint in {"/api/tags", "/api/version", "/api/show"} else self.config["timeout"]
        try:
            with self.opener.open(request, timeout=timeout) as response:
                return json.load(response)
        except HTTPError as error:
            self.check_context_error(error)
            raise

    def record_context(self, report):
        self.contexts.append(dict(validate_notice(report)))
        self.contexts = self.contexts[-128:]
        self.context_notice(dict(report))

    def context_notice(self, report):
        if report["status"] != "fits":
            print(f"Context {report['status']}: estimated {report['total_estimate']}/{report['context_window']} "
                  f"tokens including output reserve; {report['compacted_messages']} messages excerpted.", flush=True)

    def check_context_error(self, error):
        if not self.contexts:
            return
        if isinstance(error, HTTPError):
            try:
                body = json.loads(error.read(4096))
                text = body.get("error", "") if isinstance(body, dict) else ""
            except (ValueError, TypeError):
                return
            finally:
                error.close()
        else:
            text = error
        if isinstance(text, str) and "context" in text.lower() and any(
                word in text.lower() for word in ("exceed", "limit", "full", "shift")):
            report = {**self.contexts[-1], "status": "blocked", "reason": "native_context_limit"}
            self.record_context(report)
            raise ContextBudgetExceeded(report)

    def admit(self, *, tools=False, vision=False, schema=False):
        key, metadata = CAPABILITIES.get(self)
        version = tuple(int(part) for part in metadata["server_version"].split("-")[0].split("+")[0].split("."))
        if version < (0, 40, 7):
            raise ValueError("Context preservation requires the verified Ollama 0.40.7 API or later")
        required = {"completion"} | ({"tools"} if tools else set()) | ({"vision"} if vision else set())
        if not required <= set(metadata["capabilities"]):
            raise ValueError("Selected model lacks required capabilities: " + ", ".join(sorted(required - set(metadata["capabilities"]))))
        if not supported_thinking(self.options.thinking, metadata["thinking_values"]):
            raise ValueError("Selected model does not advertise the requested thinking setting; select Model default or a supported value")
        if schema:
            def probe():
                started = time.perf_counter()
                thinking = False if supported_thinking(False, metadata["thinking_values"]) else self.options.thinking
                response = self.request("/api/chat", {"model": self.config["name"], "stream": False,
                    "truncate": False, "shift": False,
                    **self.options.payload(), "options": {"num_ctx": 2048, "num_predict": 64, "temperature": 0},
                    "think": thinking,
                    "messages": [{"role": "user", "content": 'Return exactly {"ok":true}.'}], "format": PROBE_SCHEMA})
                self.probe_count += 1
                self.probe_seconds += time.perf_counter() - started
                if response.get("done") is not True or response.get("done_reason") != "stop" or response.get("remote_model") or response.get("remote_host"):
                    return False
                try:
                    value = json.loads(response["message"]["content"])
                    return isinstance(value, dict) and set(value) == {"ok"} and value["ok"] is True
                except (KeyError, TypeError, ValueError):
                    return False
            metadata = CAPABILITIES.schema(key, probe)
            current, _ = CAPABILITIES.get(self)
            if current != key:
                raise ValueError("Model identity changed during capability probing; retry admission")
        return metadata

    def payload(self, messages, *, stream=False, tools=None, schema=None):
        self.admit(tools=bool(tools), vision=any(m.get("images") for m in messages), schema=bool(schema))
        try:
            messages, report = prepare(messages, self.options.context, self.options.max_output, tools=tools, schema=schema)
        except ContextBudgetExceeded as error:
            self.record_context(error.report)
            raise
        self.record_context(report)
        payload = {"model": self.config["name"], "messages": messages, "stream": stream,
                   "truncate": False, "shift": False, **self.options.payload()}
        if tools:
            payload["tools"] = tools
        if schema:
            payload["format"] = schema
        return payload

    def record_completion(self, response, started, first=None, first_token=None):
        self.record_usage(response)
        reason = response.get("done_reason")
        reason = reason if isinstance(reason, str) and reason in {"stop", "length", "load", "unload"} else "unknown"
        if response.get("done") is not True:
            reason = "missing_final"
        def observed(name):
            value = response.get(name)
            return value if type(value) is int and 0 <= value <= 86_400_000_000_000 else None
        self.inferences.append({"finish_reason": reason,
            "prompt_tokens": observed("prompt_eval_count"), "load_ns": observed("load_duration"),
            "prompt_ns": observed("prompt_eval_duration"), "generation_ns": observed("eval_duration"),
            "total_ns": observed("total_duration"), "first_content_seconds": first,
            "first_token_seconds": first_token,
            "wall_seconds": time.perf_counter() - started})
        if len(self.inferences) > 128:
            self.inferences.pop(0)
            self.omitted_calls += 1
        if reason != "stop":
            raise InferenceIncomplete(reason)

    def inference(self):
        return {"version": 1, "calls": list(self.inferences), "compatibility_probes": self.probe_count,
                "compatibility_probe_seconds": self.probe_seconds, "omitted_calls": self.omitted_calls,
                "last_context": dict(self.contexts[-1]) if self.contexts else None}

    def chat(self, messages, tools=None, schema=None):
        payload = self.payload(messages, tools=tools, schema=schema)
        started = time.perf_counter()
        response = self.request("/api/chat", payload)
        if response.get("remote_model") or response.get("remote_host"):
            raise ValueError("Remote inference response rejected")
        self.record_completion(response, started)
        return response["message"]

    def stream_chat(self, messages):
        payload = self.payload(messages, stream=True)
        request = Request(self.config["url"].rstrip("/") + "/api/chat",
                          data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        started, first, first_token = time.perf_counter(), None, None
        try:
            response = self.opener.open(request, timeout=self.config["timeout"])
        except HTTPError as error:
            self.check_context_error(error)
            raise
        with response:
            for line in response:
                chunk = json.loads(line)
                if "error" in chunk:
                    self.check_context_error(chunk["error"])
                    raise RuntimeError(chunk["error"])
                if chunk.get("remote_model") or chunk.get("remote_host"):
                    raise ValueError("Remote inference response rejected")
                content = chunk.get("message", {}).get("content", "")
                if first_token is None and (content or chunk.get("message", {}).get("thinking")):
                    first_token = time.perf_counter() - started
                if content:
                    if first is None:
                        first = time.perf_counter() - started
                    yield content
                if chunk.get("done"):
                    self.record_completion(chunk, started, first, first_token)
                    return
            self.record_completion({}, started, first, first_token)
