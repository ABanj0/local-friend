"""Bounded content-free observations, never execution authority or task certification."""
import hashlib
import json
import math
import threading
import time
import uuid
from contextlib import contextmanager

from .safety import Denied, Stopped

MAX_SPANS = 512
MAX_NS = 86_400 * 1_000_000_000
TOOLS = frozenset({"files", "read_file", "mcp_project_read", "search_files", "apply_patch", "write_file", "command", "start_command",
    "command_status", "stop_command", "git", "browser_open", "browser_read", "browser_click", "browser_fill",
    "browser_download", "browser_screenshot", "browser_intervene", "desktop_launch", "desktop_inspect",
    "desktop_control", "desktop_input", "desktop_screenshot", "unknown_tool"})
KINDS = {"run", "plan", "step", "model", "tool", "approval", "cleanup"}
STATUSES = {"running", "observed", "approved", "denied", "expired", "invalid_input", "timeout", "transport_error",
            "error", "execution_failed", "verification_failed", "inconclusive", "reported", "planned", "no_actions",
            "blocked", "failed", "cancelled", "interrupted"}
PARENTS = {"plan": {"run"}, "step": {"run"}, "model": {"run", "plan", "step"},
           "tool": {"run", "step"}, "approval": {"tool", "approval"}, "cleanup": {"run"}}


def hex_id(value, length=32):
    return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)


def exception_status(error):
    if isinstance(error, (Stopped, KeyboardInterrupt)):
        return "cancelled"
    if isinstance(error, Denied):
        return "denied"
    if isinstance(error, (TypeError, ValueError)):
        return "invalid_input"
    if isinstance(error, TimeoutError):
        return "timeout"
    return "transport_error" if isinstance(error, (OSError, EOFError)) else "error"


def tool_status(result):
    if result.get("ok") is not True:
        return {"Denied": "denied", "TypeError": "invalid_input", "ValueError": "invalid_input",
                "TimeoutError": "timeout", "OSError": "transport_error", "ConnectionError": "transport_error",
                "BackgroundNotReady": "execution_failed", "PatchIncomplete": "execution_failed"}.get(result.get("error"), "error")
    data = result.get("untrusted_data", {})
    checks = [data["verification"]] if isinstance(data.get("verification"), dict) else data.get("verifications", [])
    if any(check.get("status") == "failed" for check in checks):
        return "verification_failed"
    if data.get("exit_code", 0) != 0:
        return "execution_failed"
    if any(check.get("status") == "inconclusive" for check in checks):
        return "inconclusive"
    return "observed"


class Span:
    def __init__(self, record):
        self.record, self.status, self.verifications = record, "observed", []


class Trace:
    def __init__(self, run_id, model, emit):
        if not hex_id(run_id):
            raise ValueError("Invalid trace run identity")
        self.run_id, self.emit = run_id, emit
        self.origin = time.perf_counter_ns()
        self.local = threading.local()
        self.count, self.dropped = 0, 0
        self.model_hash = hashlib.sha256(str(model.get("name", "")).encode()).hexdigest()
        selected = {key: model.get(key) for key in ("name", "url", "context", "temperature", "timeout", "max_output", "max_steps", "max_failures")}
        self.settings_hash = hashlib.sha256(json.dumps(selected, sort_keys=True, default=lambda _: None).encode()).hexdigest()

    def stack(self):
        if not hasattr(self.local, "stack"):
            self.local.stack = []
        return self.local.stack

    def context(self):
        stack = self.stack()
        return {"run_id": self.run_id,
                "step_id": next((span.record["id"] for span in reversed(stack) if span.record["kind"] == "step"), None),
                "call_id": next((span.record["id"] for span in reversed(stack) if span.record["kind"] == "tool"), None)}

    def start(self, kind, *, index=None, tool=None):
        if self.count >= MAX_SPANS:
            self.dropped += 1
            return Span(None)
        stack = self.stack()
        record = {"version": 1, "run_id": self.run_id, "id": self.run_id if kind == "run" else uuid.uuid4().hex,
                  "parent": stack[-1].record["id"] if stack else None, "kind": kind, "index": index,
                  "tool": tool if isinstance(tool, str) and tool in TOOLS else "unknown_tool" if kind == "tool" else None,
                  "phase": "started", "status": "running", "start_ns": time.perf_counter_ns() - self.origin,
                  "duration_ns": None, "verification_ids": [],
                  "model_sha256": self.model_hash if kind == "run" else None,
                  "settings_sha256": self.settings_hash if kind == "run" else None}
        span = Span(record)
        self.count += 1
        self.emit(record)
        stack.append(span)
        return span

    def finish(self, span, status=None):
        if span.record is None:
            return
        record = span.record
        if not self.stack() or self.stack()[-1] is not span:
            raise ValueError("Trace spans must close in order")
        self.stack().pop()
        self.emit({**record, "phase": "finished", "status": status or span.status,
                   "duration_ns": time.perf_counter_ns() - self.origin - record["start_ns"],
                   "verification_ids": span.verifications[:8]})

    @contextmanager
    def span(self, kind, **kwargs):
        span = self.start(kind, **kwargs)
        try:
            yield span
        except BaseException as error:
            span.status = exception_status(error)
            raise
        finally:
            self.finish(span)


def validate(record, run_id, states):
    fields = {"version", "run_id", "id", "parent", "kind", "index", "tool", "phase", "status", "start_ns",
              "duration_ns", "verification_ids", "model_sha256", "settings_sha256"}
    if (not isinstance(record, dict) or set(record) != fields or type(record["version"]) is not int
            or record["version"] != 1 or record["run_id"] != run_id or not hex_id(record["id"])):
        raise ValueError("Invalid trace identity or fields")
    kind, phase, status = record["kind"], record["phase"], record["status"]
    if (not isinstance(kind, str) or kind not in KINDS or not isinstance(phase, str) or phase not in {"started", "finished"}
            or not isinstance(status, str) or status not in STATUSES
            or type(record["start_ns"]) is not int or not 0 <= record["start_ns"] <= MAX_NS):
        raise ValueError("Invalid trace kind or timing")
    if ((kind == "step" and (type(record["index"]) is not int or not 1 <= record["index"] <= 10000))
            or kind != "step" and record["index"] is not None
            or kind == "tool" and (not isinstance(record["tool"], str) or record["tool"] not in TOOLS)
            or kind != "tool" and record["tool"] is not None):
        raise ValueError("Invalid trace step/tool")
    checks = record["verification_ids"]
    if type(checks) is not list or len(checks) > 8 or not all(hex_id(value) for value in checks) or len(set(checks)) != len(checks):
        raise ValueError("Invalid trace verification references")
    if kind == "run":
        if record["id"] != run_id or record["parent"] is not None or not all(hex_id(record[key], 64) for key in ("model_sha256", "settings_sha256")):
            raise ValueError("Invalid trace run metadata")
    elif (not hex_id(record["parent"]) or record["model_sha256"] is not None or record["settings_sha256"] is not None):
        raise ValueError("Invalid trace parent metadata")
    if phase == "started":
        parent = states.get(record["parent"])
        if (len(states) >= MAX_SPANS or record["id"] in states or status != "running"
                or record["duration_ns"] is not None or checks
                or kind != "run" and (not parent or parent["phase"] != "started"
                    or parent["kind"] not in PARENTS[kind] or record["start_ns"] < parent["start_ns"])):
            raise ValueError("Invalid trace start or budget")
    else:
        before = states.get(record["id"])
        if (not before or before["phase"] != "started" or status == "running"
                or type(record["duration_ns"]) is not int or not 0 <= record["duration_ns"] <= MAX_NS
                or any(record[key] != before[key] for key in fields - {"phase", "status", "duration_ns", "verification_ids"})
                or any(item["parent"] == record["id"] and (item["phase"] == "started"
                    or item["start_ns"] + item["duration_ns"] > record["start_ns"] + record["duration_ns"]) for item in states.values())):
            raise ValueError("Invalid trace finish")
    states[record["id"]] = dict(record)
    return dict(record)


def union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def length(intervals):
    return sum(end - start for start, end in union(intervals))


def summary(spans, terminal):
    finished = [span for span in spans if span["phase"] == "finished"]
    intervals = {kind: [(span["start_ns"], span["start_ns"] + span["duration_ns"]) for span in finished if span["kind"] == kind]
                 for kind in KINDS}
    waits, tools = union(intervals["approval"]), union(intervals["tool"])
    overlap = sum(max(0, min(end, b) - max(start, a)) for start, end in waits for a, b in tools)
    root = next((span for span in finished if span["kind"] == "run"), None)
    root_ns = root["duration_ns"] if root else None
    measured = length(intervals["model"] + tools + intervals["cleanup"])
    timing = {"worker_wall_ms": root_ns / 1e6 if root_ns is not None else None,
              "model_ms": length(intervals["model"]) / 1e6, "tool_active_ms": (length(tools) - overlap) / 1e6,
              "approval_ms": length(waits) / 1e6, "cleanup_ms": length(intervals["cleanup"]) / 1e6,
              "other_ms": max(0, root_ns - measured) / 1e6 if root_ns is not None else None,
              "plan_wall_ms": length(intervals["plan"]) / 1e6}
    counts = {}
    for span in finished:
        if span["kind"] == "tool":
            counts[span["status"]] = counts.get(span["status"], 0) + 1
    incomplete = sum(span["phase"] != "finished" for span in spans)
    return {"latency_ms": timing, "tool_outcomes": counts, "incomplete_spans": incomplete,
            "incomplete_state": "interrupted" if terminal else "running", "task_certification": "not_assessed"}


def numeric_metrics(value):
    if not isinstance(value, dict):
        return None
    result = {}
    for key in ("generated_tokens", "tokens_per_second", "model_calls", "elapsed_seconds"):
        item = value.get(key)
        if item is None and key == "tokens_per_second":
            result[key] = None
        elif type(item) in {int, float} and 0 <= item <= 2**63 - 1 and math.isfinite(item):
            result[key] = item
        else:
            return None
    scope = value.get("scope")
    result["scope"] = scope if isinstance(scope, str) and scope in {"response", "task"} else "unknown"
    return result


def diagnostic(task, records, checks, *, truncated=False):
    states, invalid = {}, 0
    for record in records:
        try:
            validate(record, task["id"], states)
        except (ValueError, TypeError, KeyError):
            invalid += 1
    result = task.get("result") or {}
    observations = result.get("observability") if isinstance(result, dict) else None
    dropped = observations.get("dropped_spans") if isinstance(observations, dict) else None
    if type(dropped) is not int or not 0 <= dropped <= 1_000_000:
        dropped = None
    terminal = task["status"] not in {"running", "waiting"}
    state = task["status"] if isinstance(task["status"], str) and task["status"] in STATUSES | {"waiting"} else "unknown"
    safe_checks = [{key: check[key] for key in ("id", "kind", "status")}
                   for check in checks if isinstance(check, dict) and hex_id(check.get("id"))
                   and isinstance(check.get("kind"), str) and check["kind"] in {"unittest", "artifact"}
                   and isinstance(check.get("status"), str) and check["status"] in {"passed", "failed", "inconclusive"}]
    return {"version": 1, "run_id": task["id"], "task_state": state, "available": bool(states),
            "partial": bool(truncated or invalid or dropped is None or dropped or any(s["phase"] != "finished" for s in states.values())),
            "invalid_records": invalid, "dropped_spans": dropped,
            "spans": [{**span, "observation_state": span["status"] if span["phase"] == "finished" else
                       "interrupted" if terminal else "running"} for span in states.values()],
            "summary": summary(list(states.values()), terminal), "verifications": safe_checks,
            "inference": numeric_metrics(result.get("metrics")) if isinstance(result, dict) else None,
            "privacy": "IDs, fixed categories, hashes and numeric observations only; no prompts, paths, logs or approval bodies"}


def exclude_values(value, forbidden):
    """Exact credential defense in addition to the content-free field allowlist."""
    removed = 0

    def visit(item):
        nonlocal removed
        if isinstance(item, str) and any(secret and secret in item for secret in forbidden):
            removed += 1
            return None
        if isinstance(item, dict):
            return {key: visit(entry) for key, entry in item.items()}
        if isinstance(item, list):
            return [visit(entry) for entry in item]
        return item

    result = visit(value)
    result["credential_values_removed"] = removed
    result["partial"] |= bool(removed)
    return result
