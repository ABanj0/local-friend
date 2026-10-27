"""Bounded operation observations; never approval authority or replay instructions."""
import hashlib
import json
import math
import time
from pathlib import Path, PurePosixPath

from local_agent.observability import MAX_NS, STATUSES, TOOLS, hex_id
from local_agent.review import fingerprint, require_unchanged
from local_agent.safety import Denied, Policy, Stopped, redact

MAX_STEPS = 128
MAX_OPERATIONS = 256
OUTCOMES = {"observed", "denied", "invalid_input", "timeout", "transport_error", "error",
            "execution_failed", "verification_failed", "inconclusive"}
EFFECTS = {"read", "filesystem", "process", "browser", "desktop", "git", "unknown"}


def require(condition):
    if not condition:
        raise ValueError("Invalid operation journal record")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def label(path, *, project=False):
    if path == "." and project:
        return path
    if (not isinstance(path, str) or not path or len(path) > 240 or path != redact(path)
            or any(ord(c) < 32 or ord(c) == 127 for c in path) or ":" in path or "\\" in path):
        return None
    parsed = PurePosixPath(path)
    if not parsed.parts or parsed.is_absolute() or parsed.as_posix() != path or {".", ".."} & set(parsed.parts):
        return None
    return path


def scope_key(root):
    root = Path(root).resolve()
    info = root.stat()
    return digest([str(root), info.st_dev, info.st_ino])


def effect(tool, arguments):
    if tool in {"files", "read_file", "mcp_project_read", "search_files", "browser_read", "browser_screenshot",
                "desktop_inspect", "desktop_screenshot"}:
        return "read"
    if tool in {"write_file", "apply_patch"}:
        return "filesystem"
    if tool in {"command", "start_command", "command_status", "stop_command"}:
        return "process"
    if tool == "git":
        return "read" if isinstance(arguments, dict) and arguments.get("action") in {"diff", "status"} else "git"
    if tool.startswith("browser_"):
        return "browser"
    if tool.startswith("desktop_"):
        return "desktop"
    return "unknown"


class Preconditions:
    def __init__(self, policy, tool, arguments):
        self.policy, self.checks, self.public = policy, [], []
        if not isinstance(arguments, dict):
            return
        changes = [arguments] if tool == "write_file" else arguments.get("changes", []) if tool == "apply_patch" else []
        if not isinstance(changes, list) or len(changes) > 8:
            return
        seen = set()
        for change in changes:
            if not isinstance(change, dict) or not isinstance(change.get("path"), str):
                continue
            try:
                target = policy.path(change["path"], write=True)
                if target.is_relative_to(policy.state):
                    continue
                relative = target.relative_to(policy.root).as_posix()
                if relative.casefold() in seen:
                    continue
                seen.add(relative.casefold())
                proposed = change.get("text")
                proposed_hash = hashlib.sha256(proposed.encode()).hexdigest() if isinstance(proposed, str) and len(proposed.encode()) <= 64000 else None
                item = {"resource_sha256": hashlib.sha256(relative.encode()).hexdigest(),
                        "path": label(relative), "observation": "unavailable", "sha256": None,
                        "version": None, "proposed_sha256": proposed_hash}
                try:
                    before = fingerprint(target, 64000)
                    self.checks.append((change["path"], target, before))
                    item.update(observation="file" if before else "missing",
                                sha256=before[-1] if before else None,
                                version=digest(before[1:-1]) if before else None)
                except (OSError, Denied):
                    pass
                self.public.append(item)
            except (OSError, Denied, ValueError):
                continue

    def unchanged(self):
        try:
            for path, target, before in self.checks:
                current = self.policy.path(path, write=True)
                require_unchanged(str(target), str(current))
                require_unchanged(before, fingerprint(current, 64000))
            return True
        except (OSError, Denied):
            return False


def preconditions(items):
    require(isinstance(items, list) and len(items) <= 8)
    require(len(json.dumps(items).encode()) <= 8192)
    seen = set()
    for item in items:
        require(isinstance(item, dict) and set(item) == {
            "resource_sha256", "path", "observation", "sha256", "version", "proposed_sha256"})
        resource = item["resource_sha256"]
        require(hex_id(resource, 64) and resource not in seen)
        seen.add(resource)
        path = item["path"]
        require(path is None or label(path) == path and hashlib.sha256(path.encode()).hexdigest() == resource)
        require(item["proposed_sha256"] is None or hex_id(item["proposed_sha256"], 64))
        if item["observation"] == "file":
            require(hex_id(item["sha256"], 64) and hex_id(item["version"], 64))
        else:
            require(item["observation"] in {"missing", "unavailable"} and item["sha256"] is None and item["version"] is None)
    return items


def intent(record):
    require(isinstance(record, dict) and set(record) == {
        "version", "id", "step", "tool", "effect", "arguments_sha256", "preconditions"})
    require(type(record["version"]) is int and record["version"] == 1 and hex_id(record["id"]) and hex_id(record["step"]))
    require(isinstance(record["tool"], str) and record["tool"] in TOOLS
            and isinstance(record["effect"], str) and record["effect"] in EFFECTS
            and hex_id(record["arguments_sha256"], 64))
    require(record["effect"] in ({"read", "git"} if record["tool"] == "git" else {effect(record["tool"], {})}))
    preconditions(record["preconditions"])
    return record


def result(record):
    require(isinstance(record, dict) and set(record) == {"version", "id", "outcome", "verification_ids"})
    require(type(record["version"]) is int and record["version"] == 1 and hex_id(record["id"])
            and isinstance(record["outcome"], str) and record["outcome"] in OUTCOMES)
    checks = record["verification_ids"]
    require(isinstance(checks, list) and len(checks) <= 8 and all(hex_id(i) for i in checks) and len(set(checks)) == len(checks))
    return record


def timestamp(value):
    return type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 1e12


def inspect_operation(store, config, task, operation):
    """Compare present artifacts, without changing outcomes or granting authority."""
    snapshot = store.journal(task)
    item = next((item for item in snapshot["operations"] if item["id"] == operation), None)
    if item is None:
        raise KeyError("Operation not found")
    with store.connection() as db:
        scope = db.execute("SELECT project,scope_key FROM tasks WHERE id=?", (task,)).fetchone()
    policy = None
    try:
        require(label(scope["project"], project=True) == scope["project"] and scope["project"] is not None)
        candidate = Policy(config, create=False)
        root = candidate.path(scope["project"], write=True)
        require(root.is_dir() and scope_key(root) == scope["scope_key"])
        candidate.root = root
        policy = candidate
    except (ValueError, OSError, Denied, Stopped):
        pass
    observations = []
    for before in item["preconditions"]:
        observation = {"path": before["path"], "resource_sha256": before["resource_sha256"],
                       "recorded": before["observation"], "current": "unavailable",
                       "matches_before": None, "matches_proposed": None}
        if policy and before["path"] is not None:
            try:
                target = policy.path(before["path"], write=True)
                require(not target.is_relative_to(policy.state))
                current = fingerprint(target, 64000)
                observation["current"] = "file" if current else "missing"
                if before["observation"] != "unavailable":
                    observation["matches_before"] = (before["observation"] == "missing" if current is None else
                        before["observation"] == "file" and current[-1] == before["sha256"]
                        and digest(current[1:-1]) == before["version"])
                if before["proposed_sha256"] is not None:
                    observation["matches_proposed"] = bool(current and current[-1] == before["proposed_sha256"])
            except (ValueError, OSError, Denied, Stopped):
                pass
        observations.append(observation)
    return {"version": 1, "operation": operation, "state": item["state"], "artifacts": observations,
            "replay_supported": False, "note": "Current file comparisons do not establish who changed a file or resolve an unknown effect. No action was repeated."}


def step(record, task):
    require(isinstance(record, dict) and set(record) == {
        "version", "run_id", "id", "parent", "kind", "index", "tool", "phase", "status",
        "start_ns", "duration_ns", "verification_ids", "model_sha256", "settings_sha256"})
    require(type(record["version"]) is int and record["version"] == 1 and record["run_id"] == task and record["parent"] == task
            and hex_id(record["id"]) and record["kind"] == "step" and record["tool"] is None
            and record["model_sha256"] is None and record["settings_sha256"] is None)
    require(type(record["index"]) is int and 1 <= record["index"] <= MAX_STEPS
            and record["phase"] in {"started", "finished"} and record["status"] in STATUSES
            and type(record["start_ns"]) is int and 0 <= record["start_ns"] <= MAX_NS)
    require(record["verification_ids"] == [])
    if record["phase"] == "started":
        require(record["status"] == "running" and record["duration_ns"] is None)
    else:
        require(record["status"] != "running" and type(record["duration_ns"]) is int
                and 0 <= record["duration_ns"] <= MAX_NS)
    return record


def reconcile(db, task):
    # No filesystem/browser/command access here. Unknown effects must never be retried.
    db.execute("UPDATE operations SET state=CASE WHEN effect='read' THEN 'interrupted' ELSE 'unknown' END,updated=? "
               "WHERE task=? AND state='intent'", (time.time(), task))
    db.execute("UPDATE execution_steps SET state=CASE WHEN EXISTS(SELECT 1 FROM operations WHERE step=execution_steps.id "
               "AND state='unknown') THEN 'unknown' ELSE 'interrupted' END,updated=? WHERE task=? AND state='running'",
               (time.time(), task))
