import difflib
import hashlib
import shutil
import sys
from pathlib import Path

from .background import BackgroundCommand, readiness_config
from .execution import backend
from .file_ops import atomic_write
from .patches import apply as apply_patch_set
from .process import run_process
from .repository_search import search as search_repository
from .review import CONFLICT, fingerprint, require_unchanged
from .safety import Denied
from .verification import command as verified_test_command
from .verification import observe_artifact


class Coding:
    def __init__(self, policy):
        self.policy = policy
        self.processes = {}
        self.output = None  # Trusted event sink; never a tool argument.
        self.background = None
        self.review_create = False  # Trusted UI configuration, never a model argument.
        self.execution = backend(policy, self._host_command, lambda event: self.output(event) if self.output else None)

    def python(self):
        if not getattr(sys, "frozen", False):
            return sys.executable
        executable = self.policy.config.get("runtime", {}).get("python") or shutil.which("python")
        if not executable:
            raise ValueError("Install Python or configure [runtime] python for development commands")
        return executable

    def files(self, path="."):
        directory = self.policy.path(path)
        result = []
        for item in directory.rglob("*"):
            self.policy.check_stop()
            if len(result) >= 500:
                break
            rel = item.relative_to(self.policy.root)
            if any(p in {".git", ".venv", "node_modules", "__pycache__"} for p in rel.parts):
                continue
            try:
                self.policy.path(str(rel))
            except Denied:
                continue
            if item.is_file():
                result.append(str(rel))
        return {"files": result, "limit": 500}

    def read(self, path):
        target = self.policy.path(path)
        if target.stat().st_size > 64000:
            raise ValueError("File exceeds 64 KB read limit; split it first")
        version = fingerprint(target, 64000)
        with target.open("rb") as source:
            raw = source.read(64001)
        require_unchanged(version, fingerprint(target, 64000))
        require_unchanged(version[-1], hashlib.sha256(raw).hexdigest())
        # Preserve the existing universal-newline text view; hashes describe raw bytes.
        return {"path": path, "text": raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"),
                "sha256": version[-1]}

    def patch(self, changes: list):
        return apply_patch_set(self.policy, changes)

    def search(self, query, path=".", limit=50):
        return search_repository(self.policy, query, path, limit)

    def write(self, path, text):
        target = self.policy.path(path, write=True)
        if len(text.encode()) > 64000:
            raise ValueError("Write exceeds 64 KB limit")
        version = fingerprint(target, 64000)
        if version is not None:
            with target.open(encoding="utf-8", newline="") as source:
                old = source.read()
            require_unchanged(version, fingerprint(target, 64000))
            if old == text:
                return {"path": path, "changed": False,
                        "verification": observe_artifact(self.policy, path, text.encode("utf-8"), target)}
            diff = "".join(difflib.unified_diff(old.splitlines(True), text.splitlines(True),
                                              fromfile=path, tofile=path))
            self.policy.confirm("overwrite_file", {"path": path, "diff": diff, "preimage_sha256": version[-1]})
        elif self.review_create:
            self.policy.confirm("create_file", {"path": path, "proposed_content": text})
        current = self.policy.path(path, write=True)
        require_unchanged(str(target), str(current))
        require_unchanged(version, fingerprint(current, 64000))
        atomic_write(self.policy, path, text, target, version)
        verification = observe_artifact(self.policy, path, text.encode("utf-8"), target)
        return {"path": path, "bytes": verification["observed_bytes"], "verification": verification}

    def command(self, name, cwd="."):
        return self.execution.command(name, cwd)

    def _host_command(self, name, cwd="."):
        if name not in self.policy.config["commands"]:
            raise Denied("Unknown command profile. Allowed profiles: "
                         + ", ".join(self.policy.config["commands"])
                         + ". For unittest, use name='test' and a workspace-relative cwd.")
        argv = [self.python() if arg == "{python}" else arg
                for arg in self.policy.config["commands"][name]]
        directory = self.policy.path(cwd)
        if name == "test":
            return verified_test_command(argv, directory, self.policy,
                instrument=self.policy.config["commands"][name][0] == "{python}" and argv[1:3] == ["-m", "unittest"],
                on_output=(lambda event: self.output({"profile": name, **event})) if self.output else None)
        self.policy.confirm("execute_code", {"argv": argv, "cwd": str(directory),
                            "warning": "Repository code runs with your Windows user permissions."})
        return run_process(argv, directory, self.policy,
                           on_output=(lambda event: self.output({"profile": name, **event})) if self.output else None)

    def start(self, name, cwd="."):
        self.execution.require("background")
        if name not in self.policy.config["commands"]:
            raise Denied("Unknown command profile")
        if name in self.processes:
            raise Denied("Stop the existing process for this profile first")
        if len(self.processes) >= 4:
            raise Denied("At most four background commands can be owned by one task")
        settings = readiness_config(self.policy.config.get("readiness", {}).get(name))
        directory = self.policy.path(cwd)
        argv = [self.python() if arg == "{python}" else arg
                for arg in self.policy.config["commands"][name]]
        self.policy.confirm("start_code", {"argv": argv, "cwd": str(directory), "readiness":
                            {key: settings[key] for key in ("url", "status", "timeout", "interval")} if settings else None,
                            "warning": "Code runs with your Windows permissions until task cleanup. Configured readiness "
                            "sends an unauthenticated GET only after checking listener ownership."})
        command = BackgroundCommand(self.policy, name, argv, directory, settings,
            output=(lambda payload: self.output({"profile": name, **payload})) if self.output else None,
            status=self.background)
        command.start()
        self.processes[name] = command
        return command.wait_ready()

    def status(self, name):
        if name not in self.processes:
            raise ValueError("Unknown owned process")
        return self.processes[name].status()

    def stop(self, name):
        if name not in self.processes:
            raise ValueError("Unknown owned process")
        result = self.processes[name].stop()
        self.processes.pop(name)
        return {"profile": name, "stopped": True, "process": result}

    def close(self):
        error = None
        for name in list(self.processes):
            try:
                self.stop(name)
            except OSError as exc:
                error = error or exc
        if error:
            raise error

    def git(self, action, cwd=".", message="", path=""):
        self.execution.require("git")
        directory = self.policy.path(cwd)
        executable = shutil.which("git")
        if not executable:
            raise RuntimeError("Git is not installed")
        base = [executable, "-c", "core.hooksPath=NUL", "-c", "core.fsmonitor=false",
                "-c", "core.pager=cat", "-c", "commit.gpgSign=false", "-c", "maintenance.auto=false",
                "-c", "gc.auto=0", "-c", "log.showSignature=false"]
        config_version = self._git_config_version(base, directory)
        commands = {"status": ["status", "--short"], "diff": ["diff", "--no-ext-diff", "--no-textconv"],
                    "log": ["log", "-5", "--oneline"], "init": ["init"],
                    "commit": ["commit", "-m", message]}
        if action == "stage":
            target = self.policy.path(path)
            if not target.is_file() or not target.is_relative_to(directory):
                raise Denied("Stage one existing file inside this repository at a time")
            commands["stage"] = ["add", "--", str(target.relative_to(directory))]
        if action not in commands:
            raise Denied("Supported Git actions: status, diff, log, init, stage, commit")
        # Even read-only Git can load configuration from an existing repository.
        if action == "commit":
            version = self._git_version(base, directory)
            diff = run_process(base + ["diff", "--cached", "--no-ext-diff", "--no-textconv"], directory, self.policy)
            if not message.strip():
                raise ValueError("A commit message is required")
            if diff["exit_code"] or diff["truncated"]:
                raise Denied("Cannot review complete staged diff; inspect and commit manually")
            require_unchanged(version, self._git_version(base, directory))
            self.policy.confirm("git_commit", {"cwd": cwd, "message": message, "staged_diff": diff,
                                              "index_sha256": version[1][-1] if version[1] else None,
                                              "signing": "Disabled: repository helpers are not permitted"})
            require_unchanged(version, self._git_version(base, directory))
        elif action == "stage":
            version = self._git_version(base, directory)
            preimage = fingerprint(target)
            if preimage is None:
                raise Denied(CONFLICT)
            self.policy.confirm("git_stage", {"cwd": cwd, "path": path, "preimage_sha256": preimage[-1]})
            require_unchanged(version, self._git_version(base, directory))
            require_unchanged(preimage, fingerprint(self.policy.path(path)))
        else:
            self.policy.confirm("git_" + action, {"cwd": cwd, "path": path})
            if action in {"status", "diff", "log"}:
                self._git_version(base, directory)  # Read commands must not follow an external worktree.
        require_unchanged(config_version, self._git_config_version(base, directory))
        return run_process(base + commands[action], directory, self.policy)

    def _git_config_version(self, base, directory):
        # Parse/fingerprint original bytes, never a redacted view that can hide NUL-delimited keys.
        config = run_process(base + ["config", "--no-includes", "--null", "--list"], directory, self.policy,
                             raw_output=True)
        if config["exit_code"] or config["truncated"]:
            raise Denied("Cannot inspect complete Git configuration")
        for record in config["output"].split("\0"):
            key, _, value = record.partition("\n")
            key = key.lower()
            if (key.startswith(("include.", "includeif."))
                    or (value and (key.startswith("filter.") and key.endswith((".clean", ".smudge", ".process"))
                                   or key.startswith("gpg.") and key.endswith(".program")
                                   or key == "gpg.program"
                                   or key.startswith("diff.") and key.endswith((".command", ".textconv"))
                                   or key in {"core.sshcommand", "core.gitproxy", "core.alternaterefscommand",
                                              "credential.helper"}))):
                raise Denied("Git helper/include configuration requires a separate manually reviewed workflow")
        return hashlib.sha256(config["output"].encode("utf-8")).hexdigest()

    def _git_version(self, base, directory):
        result = run_process(base + ["rev-parse", "--path-format=absolute", "--git-path", "index",
                                     "--git-path", "HEAD", "--git-common-dir", "--show-toplevel"],
                             directory, self.policy, raw_output=True)
        paths = result["output"].splitlines()
        if result["exit_code"] or result["truncated"] or len(paths) != 4:
            raise Denied("Cannot identify repository resources for review")
        for value in paths:
            self.policy.no_links(Path(value))
        index, head, common, root = [Path(value).resolve() for value in paths]
        if any(not p.is_relative_to(self.policy.root) for p in (index, head, common, root)):
            raise Denied("Repository metadata must stay inside the approved workspace")
        tree = run_process(base + ["rev-parse", "--verify", "--quiet", "HEAD^{tree}"], directory, self.policy,
                           raw_output=True)
        if tree["truncated"] or tree["exit_code"] not in {0, 1}:
            raise Denied("Cannot identify the reviewed HEAD tree")
        return (str(root), fingerprint(index), fingerprint(head), tree["output"], tree["exit_code"],
                self._git_config_version(base, directory))
