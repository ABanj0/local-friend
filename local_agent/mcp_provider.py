"""Opt-in MCP adapter using the pinned official session SDK and bounded stdio pipes.

Fresh owned server per call avoids persistent session/reconnect/replay authority.
The small custom transport bounds frames *before* SDK JSON parsing; SDK's default
stdio transport buffers an unterminated line without a byte limit.
"""
import hashlib
import json
import sys
import threading
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .mcp_contract import (
    MAX_FILE,
    MAX_FRAME,
    MAX_TRAFFIC,
    SDK_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    MCPError,
    MCPReviewRequired,
    approved_path,
    descriptor,
    settings,
)
from .mcp_process import finish, start
from .review import fingerprint, require_unchanged
from .safety import Denied, Stopped, redact


def require_sdk():
    try:
        valid = version("mcp") == SDK_VERSION and version("mcp-types") == SDK_VERSION
    except PackageNotFoundError:
        valid = False
    if not valid:
        raise MCPError("MCP requires mcp==2.3.0 and mcp-types==2.3.0; install the mcp project extra")


def server_command(policy):
    args = ["--root", str(policy.root), "--state", str(policy.state)]
    if getattr(sys, "frozen", False):
        return [sys.executable, "--mcp-project-server", *args]
    return [sys.executable, "-I", str(Path(__file__).with_name("mcp_server.py")), *args]


def errors(exc):
    for child in getattr(exc, "exceptions", ()):
        yield from errors(child)
    yield exc


@asynccontextmanager
async def transport(argv, cwd):
    import anyio
    import mcp_types as types
    from mcp.shared.message import SessionMessage

    proc, job = start(argv, cwd)
    try:
        incoming, receive = anyio.create_memory_object_stream(0)
        send, outgoing = anyio.create_memory_object_stream(0)
        pending, total = set(), 0

        async def reader():
            nonlocal total
            async with incoming:
                while True:
                    line = await anyio.to_thread.run_sync(
                        proc.stdout.readline, MAX_FRAME + 1, abandon_on_cancel=True)
                    if not line:
                        return
                    total += len(line)
                    if len(line) > MAX_FRAME or total > MAX_TRAFFIC or not line.endswith(b"\n"):
                        raise MCPError("MCP output exceeded its transport budget")
                    try:
                        data = json.loads(line)
                        # This provider accepts responses only, never server requests/notifications.
                        if (type(data) is not dict or type(data.get("id")) is not int
                                or data["id"] not in pending or data.get("jsonrpc") != "2.0"
                                or set(data) not in ({"jsonrpc", "id", "result"},
                                                     {"jsonrpc", "id", "error"})):
                            raise ValueError()
                        message = types.jsonrpc_message_adapter.validate_json(line)
                    except (ValueError, TypeError):
                        raise MCPError("MCP sent an invalid or unexpected response") from None
                    pending.remove(data["id"])
                    await incoming.send(SessionMessage(message))

        def write(raw):
            proc.stdin.write(raw)
            proc.stdin.flush()

        async def writer():
            async with outgoing:
                async for item in outgoing:
                    data = item.message.model_dump(by_alias=True, exclude_unset=True)
                    raw = (json.dumps(data) + "\n").encode()
                    if len(raw) > 4096:
                        raise MCPError("MCP request exceeded its transport budget")
                    if "id" in data:
                        pending.add(data["id"])
                    await anyio.to_thread.run_sync(write, raw, abandon_on_cancel=True)

        async with anyio.create_task_group() as group:
            group.start_soon(reader)
            group.start_soon(writer)
            try:
                yield receive, send
            finally:
                group.cancel_scope.cancel()
    finally:
        # Kill before closing pipes: an inherited/hung reader must not hold cleanup open.
        finish(proc, job)


class ProjectProvider:
    def __init__(self, policy):
        self.policy = policy
        self.enabled, self.timeout = settings(policy.config)
        self._closed = threading.Event()

    def close(self):
        self._closed.set()

    def read(self, path):
        self.policy.check_stop()
        if not self.enabled or self._closed.is_set():
            raise Denied("MCP project provider is disabled or closed")
        target = approved_path(self.policy, path)
        expected = fingerprint(target, MAX_FILE)
        if expected is None:
            raise Denied("MCP requires an existing regular text file")
        require_sdk()
        import anyio
        from mcp import ClientSession

        stopped, result = False, None

        async def exchange():
            nonlocal stopped, result
            async with anyio.create_task_group() as group:
                async def stop_watch():
                    nonlocal stopped
                    while True:
                        try:
                            self.policy.check_stop()
                            if self._closed.is_set():
                                raise Stopped()
                        except Stopped:
                            stopped = True
                            group.cancel_scope.cancel()
                            return
                        await anyio.sleep(.05)

                group.start_soon(stop_watch)
                try:
                    with anyio.fail_after(self.timeout):
                        async with transport(server_command(self.policy), Path(__file__).parent.parent) as streams:  # noqa: SIM117 -- streams construct the session
                            async with ClientSession(*streams, read_timeout_seconds=self.timeout) as session:
                                hello = await session.initialize()
                                if (hello.server_info.name != SERVER_NAME
                                        or hello.server_info.version != SERVER_VERSION):
                                    raise MCPReviewRequired("MCP server changed; review the pinned provider before use")
                                catalog = await session.list_tools()
                                tools = [t.model_dump(mode="json", by_alias=True, exclude_none=True)
                                         for t in catalog.tools]
                                if catalog.next_cursor is not None or tools != [descriptor()]:
                                    raise MCPReviewRequired("MCP schema changed; review the pinned provider before use")
                                response = await session.call_tool("read_text", {"path": path})
                                body = response.model_dump(mode="json", by_alias=True, exclude_none=True)
                                if (set(body) != {"content", "isError", "resultType"}
                                        or body["isError"] or body["resultType"] != "complete"
                                        or len(body["content"]) != 1
                                        or set(body["content"][0]) != {"type", "text"}
                                        or body["content"][0]["type"] != "text"):
                                    raise MCPError("MCP read failed or returned unsupported content")
                                result = json.loads(body["content"][0]["text"])
                finally:
                    group.cancel_scope.cancel()

        try:
            anyio.run(exchange)
        except Exception as exc:  # noqa: BLE001 -- normalize SDK/task-group errors without raw data
            for error in errors(exc):
                if isinstance(error, (MCPReviewRequired, MCPError, TimeoutError)):
                    raise error from None
            raise MCPError("MCP transport failed; check the installed provider and dependencies") from None
        if stopped:
            raise Stopped("MCP read cancelled; owned server closed")
        self.policy.check_stop()
        if (type(result) is not dict or set(result) != {"path", "text", "sha256", "bytes"}
                or result["path"] != path or type(result["text"]) is not str
                or len(result["text"].encode()) > MAX_FRAME // 2
                or type(result["bytes"]) is not int or result["bytes"] != expected[-3]
                or result["sha256"] != expected[-1]):
            raise MCPError("MCP returned invalid project read metadata")
        require_unchanged(target, approved_path(self.policy, path))
        require_unchanged(expected, fingerprint(target, MAX_FILE))
        # Redaction precedes both model observations and durable tool events.
        result["text"] = redact(result["text"])
        result["provider"] = SERVER_NAME
        result["schema_sha256"] = hashlib.sha256(json.dumps(descriptor(), sort_keys=True).encode()).hexdigest()
        return result
