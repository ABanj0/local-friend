"""Opt-in, leased disposable VM execution for synchronous Python command profiles."""
import base64
import ctypes
import fnmatch
import hashlib
import ipaddress
import json
import os
import tempfile
import time
import uuid
from pathlib import Path

from .hyperv_control import Controller, Settings, regular
from .hyperv_guest import FETCH, LOAD_STAGE, STAGE
from .process import run_process
from .review import fingerprint, require_unchanged
from .safety import Denied
from .verification import RUNNER, validate


def process_identity(pid):
    """PID plus creation time, and only a currently live process; no psutil dependency."""
    from ctypes import wintypes
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
    api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x1000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:  # No process has this PID.
            return None
        raise Denied("VM lease process identity is inaccessible; do not assume its owner is dead")
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        code = wintypes.DWORD()
        if not api.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]) or not api.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise Denied("Cannot establish VM lease process identity")
        if code.value != 259:
            return None
        return times[0].dwHighDateTime << 32 | times[0].dwLowDateTime
    finally:
        api.CloseHandle(handle)


def lease_path(settings):
    return settings.storage / "agent-execution-lease.json"


def read_lease(settings):
    path = lease_path(settings)
    if not path.exists():
        return None
    regular(path)
    with path.open("rb") as stream:
        raw = stream.read(4097)
    try:
        value = json.loads(raw)
        if (len(raw) > 4096 or set(value) != {"vm_id", "run_id", "pid", "created"}
                or value["vm_id"] != settings.vm_id or type(value["pid"]) is not int or not 0 < value["pid"] < 2**32
                or type(value["created"]) is not int or value["created"] <= 0
                or not isinstance(value["run_id"], str) or len(value["run_id"]) != 32
                or any(c not in "0123456789abcdef" for c in value["run_id"])):
            raise ValueError
        return value
    except (ValueError, TypeError, KeyError):
        raise Denied("Invalid VM ownership lease; preserve it for inspection") from None


def recover(config, owner=None):
    settings = Settings.parse(config)
    value = read_lease(settings)
    if value is None or owner is not None and value["pid"] != owner:
        return
    if process_identity(value["pid"]) == value["created"]:
        return  # Never stop a live unrelated/other manager's task.
    Controller(settings, value["run_id"]).call("stop")
    require_unchanged(value, read_lease(settings))
    lease_path(settings).unlink()


def inputs(policy, patterns, cwd):
    """Freeze reviewed bytes and resource versions; reject links and incomplete selection."""
    files = {}
    entries, deadline = 0, time.monotonic() + 3
    for pattern in patterns:
        found = False
        parent = Path(pattern).parent
        policy.no_links(policy.root / parent)
        for path in policy.path(parent).iterdir():
            policy.check_stop()
            entries += 1
            if entries > 10000 or time.monotonic() > deadline:
                raise Denied("VM input enumeration exceeded its coverage/time budget")
            if not fnmatch.fnmatchcase(path.name.casefold(), Path(pattern).name.casefold()):
                continue
            if not path.is_file():
                continue
            found = True
            relative = path.relative_to(policy.root).as_posix()
            if any(p.startswith(".") or p in {"node_modules", "__pycache__"} for p in path.relative_to(policy.root).parts):
                raise Denied("Hidden, control and dependency files are not VM staging inputs")
            policy.no_links(policy.root / relative)
            target = policy.path(relative)
            policy.no_links(target)
            version = fingerprint(target, 256 * 1024)
            raw = target.read_bytes()
            require_unchanged(version, fingerprint(policy.path(relative), 256 * 1024))
            if len(raw) > 256 * 1024:
                raise Denied("VM input exceeds its byte budget")
            if relative.casefold() in {p.casefold() for p in files} and relative not in files:
                raise Denied("Ambiguous VM input paths")
            files[relative] = {"raw": raw, "version": version}
            if len(files) > 200 or sum(len(f["raw"]) for f in files.values()) > 4 * 1024**2:
                raise Denied("VM staging exceeds its file/byte budget")
        if not found:
            raise Denied("A configured VM input pattern matched no files; staging is incomplete")
    if not files:
        raise Denied("No approved VM inputs selected")
    directory = policy.path(cwd)
    if not directory.is_dir():
        raise Denied("Working directory must exist inside the approved project")
    return files, directory.relative_to(policy.root).as_posix()


class HyperVExecution:
    def __init__(self, policy, output):
        self.policy, self.output = policy, output
        self.settings = Settings.parse(policy.config)
        self.controller = Controller(self.settings)

    def require(self, operation):
        raise Denied("Hyper-V supports synchronous Python command profiles only; this operation cannot fall back to host execution")

    def _ssh(self, address, code, argument=None, *, stdin=False):
        s = self.settings
        executable = Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/OpenSSH/ssh.exe"
        regular(executable, serviced_system_file=True)
        options = {"IdentitiesOnly": "yes", "IdentityAgent": "none", "BatchMode": "yes",
                   "PasswordAuthentication": "no", "KbdInteractiveAuthentication": "no",
                   "StrictHostKeyChecking": "yes", "VerifyHostKeyDNS": "no", "GlobalKnownHostsFile": "NUL",
                   "UserKnownHostsFile": str(s.known_hosts), "HostKeyAlias": "local-agent-hyperv-" + s.vm_id,
                   "ForwardAgent": "no", "ClearAllForwardings": "yes", "ProxyCommand": "none", "ProxyJump": "none",
                   "ConnectTimeout": "3", "ConnectionAttempts": "1"}
        argv = [str(executable), "-F", "NUL", "-T", "-i", str(s.identity_file)]
        for key, value in options.items():
            argv += ["-o", f"{key}={value}"]
        encoded = base64.b64encode(code.encode()).decode()
        python = s.python.replace("'", "''")
        expression = f"import base64;exec(base64.b64decode('{encoded}'))"
        script = ("$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
                  "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);$OutputEncoding=[Console]::OutputEncoding;"
                  f"if($env:USERNAME -ine '{s.ssh_user}' -or @([Security.Principal.WindowsIdentity]::GetCurrent().Groups|"
                  "Where-Object Value -eq 'S-1-5-32-544').Count -gt 0){throw 'Guest Standard-user identity required'};"
                  f"{'$input | ' if stdin else ''}& '{python}' -I -c \"{expression}\"")
        if argument is not None:
            # Base64 avoids native Windows PowerShell's argument-quote transformations.
            script += " '" + base64.b64encode(json.dumps(argument).encode()).decode() + "'"
        script += ";exit $LASTEXITCODE"
        shell = base64.b64encode(script.encode("utf-16-le")).decode()
        return [*argv, f"{s.ssh_user}@{address}", "powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", shell]

    @staticmethod
    def _address(state):
        addresses = []
        for item in state["addresses"]:
            try:
                address = ipaddress.IPv4Address(item)
                if address.is_private and not address.is_link_local and not address.is_loopback:
                    addresses.append(str(address))
            except (ValueError, TypeError):
                pass
        if len(addresses) != 1:
            raise Denied("Owned VM has no unique private IPv4 address yet")
        return addresses[0]

    def command(self, name, cwd="."):
        policy, s = self.policy, self.settings
        profile = policy.config.get("commands", {}).get(name)
        if (not isinstance(profile, list) or not profile or profile[0] != "{python}"
                or len(profile) > 128 or any(not isinstance(a, str) or len(a) > 4096 or "\x00" in a for a in profile)):
            raise Denied("Isolated commands require a configured {python} profile; no host fallback")
        files, relative_cwd = inputs(policy, s.inputs, cwd)
        state = self.controller.call("inspect")
        if state["state"] != "Off":
            raise Denied("The dedicated VM must be off before claiming a new task; existing session preserved")
        if read_lease(s) is not None:
            raise Denied("Dedicated VM already has an ownership lease; inspect or recover its previous task")
        manifest = [{"path": p, "bytes": len(v["raw"]), "sha256": hashlib.sha256(v["raw"]).hexdigest()} for p, v in sorted(files.items())]
        argv = [s.python, *profile[1:]]
        policy.confirm("execute_code", {"argv": argv, "cwd": relative_cwd, "backend": "hyperv",
                       "vm_id": s.vm_id, "checkpoint": s.checkpoint_id, "inputs": manifest,
                       "warning": "Reset the dedicated VM, run with no initiated network access, return bounded output/counts, then power it off. Guest file changes are discarded; host file edits remain separately reviewed."})
        for path, value in files.items():
            policy.no_links(policy.root / path)
            require_unchanged(value["version"], fingerprint(policy.path(path), 256 * 1024))
        ident = uuid.uuid4().hex
        lease = {"vm_id": s.vm_id, "run_id": ident, "pid": os.getpid(), "created": process_identity(os.getpid())}
        if lease["created"] is None:
            raise Denied("Cannot establish live VM task ownership")
        try:
            self.controller.run_id = ident
            with lease_path(s).open("x", encoding="utf-8") as stream:
                json.dump(lease, stream)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            raise Denied("Another task claimed the dedicated VM") from None
        try:
            policy.check_stop()
            self.controller.call("prepare")
            deadline = time.monotonic() + s.boot_timeout
            address = None
            while time.monotonic() < deadline:
                policy.check_stop()
                state = self.controller.call("bootstrap")  # Policy/ownership failures stop immediately.
                try:
                    address = self._address(state)
                except Denied:
                    time.sleep(.2)
                    continue
                try:
                    probe = run_process(self._ssh(address, 'print("LOCAL-AGENT-VM-READY")'), policy.state, policy,
                                        timeout=8, raw_output=True, windows_ssh=True)
                    if probe["exit_code"] == 0 and probe["output"].strip() == "LOCAL-AGENT-VM-READY":
                        break
                    if any(message in probe["output"] for message in (
                            "REMOTE HOST IDENTIFICATION HAS CHANGED", "Host key verification failed",
                            "Permission denied (publickey")):
                        raise Denied("Guest SSH identity/key validation failed; preserve the pinned key and inspect configuration")
                except TimeoutError:
                    pass
                time.sleep(.2)
            else:
                raise Denied("Dedicated VM did not become ready within its boot budget")
            sealed = self.controller.call("seal")
            require_unchanged(address, self._address(sealed))
            self.controller.call("inspect")  # No project bytes or command run before sealing.
            instrument = name == "test" and profile[1:3] == ["-m", "unittest"]
            payload = {"root": s.guest_root, "run_id": ident, "cwd": relative_cwd, "argv": argv,
                       "timeout": s.timeout, "runner": RUNNER if instrument else None,
                       "files": [{"path": p, "data": base64.b64encode(v["raw"]).decode()} for p, v in sorted(files.items())]}
            with tempfile.TemporaryFile(dir=policy.state) as stream:
                loader = base64.b64encode(STAGE.encode()) + b"\n"
                if len(loader) > 16384:
                    raise Denied("Trusted guest bootstrap exceeds its transport budget")
                stream.write(loader + json.dumps(payload).encode());stream.seek(0)
                outcome = run_process(self._ssh(address, LOAD_STAGE, stdin=True), policy.state, policy, timeout=s.timeout + 15,
                                      stdin=stream, windows_ssh=True,
                                      on_output=(lambda event: self.output({"profile": name, **event})))
            if name == "test":
                counts = None
                observed = run_process(self._ssh(address, FETCH, {"root": s.guest_root, "run_id": ident}),
                                       policy.state, policy, timeout=15, raw_output=True, windows_ssh=True)
                try:
                    result = json.loads(observed["output"])
                    if (observed["exit_code"] == 0 and not observed["truncated"]
                            and set(result) == {"schema", "run_id", "exit_code", "counts"}
                            and type(result["schema"]) is int and result["schema"] == 1 and result["run_id"] == ident
                            and type(result["exit_code"]) is int and result["exit_code"] == outcome["exit_code"]):
                        counts = result["counts"] if instrument else None
                except (ValueError, TypeError):
                    pass
                record = {"id": ident, "kind": "unittest", "version": 1, "profile": "test",
                          "command_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
                          "exit_code": outcome["exit_code"], "counts": counts}
                try:
                    outcome["verification"] = validate(record)
                except ValueError:
                    outcome["verification"] = validate({**record, "counts": None})
            outcome["execution"] = {"backend": "hyperv", "vm_id": s.vm_id, "checkpoint": s.checkpoint_id,
                                    "input_count": len(manifest), "guest_file_changes_imported": False}
            return outcome
        finally:
            self.controller.call("stop")
            require_unchanged(lease, read_lease(s))
            lease_path(s).unlink()
