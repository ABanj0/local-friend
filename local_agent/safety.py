"""Deny-by-default action boundaries. This is not an OS sandbox."""
import hashlib
import json
import os
import stat
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from .redaction import redact_text


class Denied(RuntimeError):
    pass


class Stopped(BaseException):
    pass


def redact(text):
    return redact_text(text)


class Policy:
    def __init__(self, config, approve=None, *, create=True):
        self.config = config
        self.root = Path(config["paths"]["workspace"]).resolve()
        self.state = Path(config["paths"]["state"]).resolve()
        if create:
            self.root.mkdir(parents=True, exist_ok=True)
            self.state.mkdir(parents=True, exist_ok=True)
        self.approve = approve or (lambda action, details: False)
        self.stop_event = threading.Event()

    def check_stop(self):
        if self.stop_event.is_set() or (self.state / "STOP").exists():
            raise Stopped("Emergency stop requested")

    def path(self, value, *, write=False):
        self.check_stop()
        # Reject Windows device paths, ADS, traversal aliases and secret stores.
        raw = str(value)
        if not raw or raw.startswith(("\\\\", "//")) or ":" in raw:
            raise Denied("Use workspace-relative paths without device or stream syntax")
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise Denied("Path must stay inside the approved workspace")
        for part in relative.parts:
            if part.endswith((".", " ")) or part.split(".")[0].upper() in {
                "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)),
                *(f"LPT{i}" for i in range(10)),
            }:
                raise Denied("Reserved or ambiguous filename")
            if part.lower() in {".env", ".ssh", ".aws", ".git", ".codex", ".agents"} or part.lower().endswith((".pem", ".key")):
                raise Denied("Credential and control directories are not file-tool inputs")
        unresolved = self.root / relative
        if write:
            self.no_links(unresolved)
        target = unresolved.resolve()
        if not target.is_relative_to(self.root):
            raise Denied("Path escapes approved workspace")
        # Do not let an external hardlink alias become a write target.
        if target.is_file() and os.stat(target).st_nlink > 1:
            raise Denied("Hardlinked files are not supported")
        return target

    def no_links(self, target):
        """Write/Git metadata inputs must have no symlink, junction or reparse ancestor."""
        if not target.is_relative_to(self.root):
            raise Denied("Path escapes approved workspace")
        current = self.root
        for part in ("", *target.relative_to(self.root).parts):
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise Denied("Symlink and reparse paths are not supported for mutation or Git metadata")

    def confirm(self, action, details):
        self.check_stop()
        if not self.approve(action, details):
            raise Denied(f"Approval denied: {action}")
        self.check_stop()

    def origin(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            raise Denied("Only HTTP(S) URLs without credentials are permitted")
        origin = f"{parsed.scheme}://{parsed.netloc.lower()}"
        if origin not in self.config["browser"]["allowed_origins"]:
            raise Denied(f"Origin is not in browser.allowed_origins: {origin}")
        return origin

    def audit(self, name, arguments, status):
        # Never persist raw prompts, arguments, page text, command output or screenshots.
        digest = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
        record = {"time": time.time(), "tool": name, "arguments_sha256": digest, "status": status}
        with (self.state / "audit.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
