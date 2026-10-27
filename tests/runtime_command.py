"""Run the same runtime contracts against source or an explicitly selected frozen EXE."""
import os
import sys
from pathlib import Path


def runtime_command():
    executable = os.getenv("FROZEN_BACKEND_TEST_EXE")
    if executable:
        path = Path(executable).resolve(strict=True)
        if path.suffix.lower() != ".exe":
            raise ValueError("Frozen acceptance requires a built Windows executable")
        return [str(path)]
    return [sys.executable, "-m", "local_agent.studio.runtime"]
