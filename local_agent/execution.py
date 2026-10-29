"""Trusted configuration chooses command execution; model arguments cannot change it."""
from typing import Protocol

from .safety import Denied


class ExecutionBackend(Protocol):
    def command(self, name, cwd="."): ...

    def require(self, operation): ...


def selected(config):
    settings = config.get("coding_execution", {})
    if not isinstance(settings, dict):
        raise Denied("coding_execution must be a trusted configuration table")
    kind = settings.get("backend", "trusted_host")
    if not isinstance(kind, str) or kind not in {"trusted_host", "hyperv"}:
        raise Denied("Unsupported coding execution backend; host fallback is forbidden")
    if kind == "trusted_host" and set(settings) - {"backend"}:
        raise Denied("Unknown trusted-host execution setting")
    return kind


def descriptor(config):
    kind = selected(config)
    return {"backend": kind, "label": "Trusted host execution" if kind == "trusted_host"
            else "Hyper-V coding execution (validated before each command)",
            "isolation_required": kind == "hyperv",
            "scope": "Synchronous coding commands only. File edits, browser and desktop actions use their existing scopes."}


class TrustedHostExecution:
    def __init__(self, command):
        self._command = command

    def command(self, name, cwd="."):
        return self._command(name, cwd)

    def require(self, operation):
        pass


def backend(policy, host_command, output):
    if selected(policy.config) == "trusted_host":
        return TrustedHostExecution(host_command)
    from .hyperv_execution import HyperVExecution
    return HyperVExecution(policy, output)


def recover(config, owner=None):
    if selected(config) == "hyperv":
        from .hyperv_execution import recover as recover_vm
        recover_vm(config, owner)
