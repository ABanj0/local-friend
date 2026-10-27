"""Literal, bounded text search under the existing file policy; no shell or regex."""
import hashlib
import json
import os
import stat
import time

from .review import require_unchanged, signature
from .safety import Denied, redact

MAX_ENTRIES = 10_000
MAX_FILES = 500
MAX_BYTES = 8 * 1024**2
MAX_FILE = 64_000
MAX_DEPTH = 20
MAX_OUTPUT = 8192
TIME_LIMIT = 3
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".runtime", ".cache", "build", "dist"}
PRIVATE_NAMES = {".npmrc", ".pypirc", ".netrc", "_netrc", ".git-credentials"}


def search(policy, query, path=".", limit=50):
    if not isinstance(query, str) or not 1 <= len(query) <= 256 or any(c in query for c in "\r\n\0"):
        raise ValueError("Search query must be one literal line of 1-256 characters")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Search match limit must be between 1 and 100")
    root = policy.path(path, write=True)  # Read-only operation with strict link checks.
    if any(part.lower().startswith(".env") or part.lower() in PRIVATE_NAMES
           for part in root.relative_to(policy.root).parts):
        raise Denied("Credential inputs are not repository search scopes")
    if root.is_relative_to(policy.state):
        raise Denied("Search cannot scan the agent state directory")
    if not root.is_dir():
        raise ValueError("Search scope must be an existing project directory")
    stats = {"visited_entries": 0, "attempted_files": 0, "scanned_files": 0, "bytes_read": 0}
    skipped = dict.fromkeys(("excluded", "denied", "nontext", "oversized", "unreadable", "changed", "depth"), 0)
    matches, reason, output_size = [], None, 0
    deadline = time.monotonic() + TIME_LIMIT
    stack = [(root, 0, signature(root.lstat()))]

    def interrupted():
        nonlocal reason
        policy.check_stop()
        if time.monotonic() >= deadline:
            reason = "time_limit"
        return reason is not None

    def scan_file(candidate, relative, before):
        nonlocal reason, output_size
        if before.st_size > MAX_FILE:
            skipped["oversized"] += 1
            return
        if stats["attempted_files"] >= MAX_FILES:
            reason = "file_limit"
            return
        if before.st_size > MAX_BYTES - stats["bytes_read"]:
            reason = "byte_limit"
            return
        if redact(relative) != relative:
            skipped["denied"] += 1  # Do not turn a private filename into a broken clickable label.
            return
        stats["attempted_files"] += 1
        try:
            current = policy.path(relative, write=True)
            require_unchanged(candidate, current)
            with current.open("rb") as source:
                require_unchanged(signature(before), signature(os.fstat(source.fileno())))
                raw = source.read(min(MAX_FILE + 1, MAX_BYTES - stats["bytes_read"]))
                stats["bytes_read"] += len(raw)
                require_unchanged(signature(before), signature(os.fstat(source.fileno())))
            require_unchanged(current, policy.path(relative, write=True))
            require_unchanged(signature(before), signature(current.lstat()))
            if len(raw) != before.st_size:
                raise Denied("Search input changed during read")
        except Denied:
            skipped["changed"] += 1
            return
        except OSError:
            skipped["unreadable"] += 1
            return
        if b"\0" in raw:
            skipped["nontext"] += 1
            return
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped["nontext"] += 1
            return
        stats["scanned_files"] += 1
        lines, safe_lines = text.splitlines(), redact(text).splitlines()
        digest = hashlib.sha256(raw).hexdigest()
        for number, line in enumerate(lines, 1):
            if interrupted():
                return
            column = line.find(query)
            if column < 0:
                continue
            safe = safe_lines[number - 1] if len(lines) == len(safe_lines) else ""
            position = safe.find(query)
            start = max(0, position - 60)
            preview = safe[start:start + 240] if position >= 0 else "[Matching text omitted by credential-pattern treatment]"
            item = {"path": relative, "line": number, "column": column + 1,
                    "text": preview, "preview_truncated": start > 0 or len(safe) > start + 240,
                    "sha256": digest}
            # ASCII JSON is a conservative upper bound for the model and UTF-8 transport.
            size = len(json.dumps(item).encode("ascii")) + 2
            if output_size + size > MAX_OUTPUT - 1024:
                reason = "output_limit"
                return
            matches.append(item)
            output_size += size
            if len(matches) >= limit:
                reason = "match_limit"
                return

    while stack and not interrupted():
        directory, depth, expected = stack.pop()
        try:
            relative_directory = str(directory.relative_to(policy.root))
            require_unchanged(directory, policy.path(relative_directory, write=True))
            require_unchanged(expected, signature(directory.lstat()))
            with os.scandir(directory) as entries:
                for entry in entries:
                    if interrupted():
                        break
                    if stats["visited_entries"] >= MAX_ENTRIES:
                        reason = "entry_limit"
                        break
                    stats["visited_entries"] += 1
                    candidate = directory / entry.name
                    relative = str(candidate.relative_to(policy.root))
                    if (entry.name.lower().startswith(".env") or entry.name.lower() in PRIVATE_NAMES
                            or candidate.is_relative_to(policy.state)):
                        skipped["excluded"] += 1
                        continue
                    try:
                        # Windows DirEntry.stat() can report zero identity/link counts;
                        # obtain real path metadata for the policy and stability checks.
                        info = candidate.lstat()
                        if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
                                or stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
                            raise Denied("Search does not follow links")
                        policy.path(relative, write=True)
                    except Denied:
                        skipped["denied"] += 1
                        continue
                    except OSError:
                        skipped["unreadable"] += 1
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        if entry.name.lower() in SKIP_DIRS:
                            skipped["excluded"] += 1
                        elif depth >= MAX_DEPTH:
                            skipped["depth"] += 1
                        else:
                            stack.append((candidate, depth + 1, signature(info)))
                    elif stat.S_ISREG(info.st_mode):
                        scan_file(candidate, relative, info)
                    else:
                        skipped["nontext"] += 1
        except Denied:
            skipped["changed"] += 1
        except OSError:
            skipped["unreadable"] += 1
    incomplete = bool(reason or any(skipped[key] for key in ("oversized", "unreadable", "changed", "depth")))
    return {"matches": matches, **stats, "skipped": skipped, "complete": not incomplete,
            "stop_reason": reason or ("skipped_inputs" if incomplete else None),
            "scope": "UTF-8 regular files; credentials, dependency descendants and agent state excluded",
            "limits": {"entries": MAX_ENTRIES, "files": MAX_FILES, "bytes": MAX_BYTES,
                       "file_bytes": MAX_FILE, "depth": MAX_DEPTH, "output_bytes": MAX_OUTPUT,
                       "seconds": TIME_LIMIT}}
