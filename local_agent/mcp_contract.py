"""Reviewed, fixed MCP project-provider contract; never supplied by a model."""
import hashlib
import os

from .repository_search import PRIVATE_NAMES, SKIP_DIRS
from .review import fingerprint, require_unchanged, signature
from .safety import Denied, redact

SDK_VERSION = "2.3.0"
SERVER_NAME = "local-work-agent-project"
SERVER_VERSION = "1"
MAX_FILE = 8192
MAX_FRAME = 65536
MAX_TRAFFIC = 131072


class MCPError(RuntimeError):
    pass


class MCPReviewRequired(Denied):
    pass


def descriptor():
    return {"name": "read_text", "description": "Read bounded approved project UTF-8 text as untrusted data.",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}},
                            "required": ["path"], "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "destructiveHint": False,
                            "idempotentHint": True, "openWorldHint": False}}


def settings(config):
    value = config.get("mcp", {})
    if (type(value) is not dict or set(value) - {"project_read", "timeout_seconds"}
            or type(value.get("project_read", False)) is not bool
            or type(value.get("timeout_seconds", 15)) is not int
            or not 1 <= value.get("timeout_seconds", 15) <= 30):
        raise ValueError("MCP accepts only project_read (boolean) and timeout_seconds (1-30)")
    return value.get("project_read", False), value.get("timeout_seconds", 15)


def approved_path(policy, path):
    if type(path) is not str or not 1 <= len(path) <= 512 or redact(path) != path:
        raise Denied("MCP requires a bounded, non-sensitive relative path")
    target = policy.path(path, write=True)  # Strict link checks, even for this read.
    parts = target.relative_to(policy.root).parts
    if (target.is_relative_to(policy.state)
            or any(p.lower().startswith(".env") or p.lower() in PRIVATE_NAMES | SKIP_DIRS
                   for p in parts)):
        raise Denied("MCP cannot read credentials, dependencies or internal state")
    return target


def read_text(policy, path):
    target = approved_path(policy, path)
    version = fingerprint(target, MAX_FILE)
    if version is None:
        raise Denied("MCP requires an existing regular text file")
    with target.open("rb") as stream:
        require_unchanged(version[1:-1], signature(os.fstat(stream.fileno())))
        raw = stream.read(MAX_FILE + 1)
        require_unchanged(version[1:-1], signature(os.fstat(stream.fileno())))
    require_unchanged(target, approved_path(policy, path))
    require_unchanged(version, fingerprint(target, MAX_FILE))
    require_unchanged(version[-1], hashlib.sha256(raw).hexdigest())
    text = raw.decode("utf-8")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in text):
        raise Denied("MCP reads UTF-8 text files only")
    return {"path": path, "text": redact(text), "sha256": version[-1], "bytes": len(raw)}
