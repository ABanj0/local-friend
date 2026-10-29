import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from http.client import HTTPException
from pathlib import Path

from .agent import Agent
from .config import load
from .execution import descriptor as execution_descriptor
from .execution import recover as recover_execution
from .model import Ollama
from .safety import Policy, Stopped, redact
from .tool_spec import PROFILES
from .tools import Tools


def approve(action, details):
    print("\nApproval required: " + action)
    print(redact(json.dumps(details, indent=2, ensure_ascii=True)))
    try:
        return input("Type APPROVE to execute this exact action (anything else denies): ") == "APPROVE"
    except (EOFError, KeyboardInterrupt):
        return False


def doctor(config):
    result = {"python": sys.version, "workspace": config["paths"]["workspace"], "coding_execution": execution_descriptor(config),
              "dependencies": {name: importlib.util.find_spec(name) is not None
                               for name in ("playwright", "pywinauto", "pyautogui", "PIL")}}
    try:
        result["ollama"] = Ollama(config["model"]).request("/api/tags")
    except (OSError, ValueError, HTTPException) as exc:
        result["ollama"] = {"available": False, "error": redact(str(exc))}
    print(json.dumps(result, indent=2))
    return 0 if all(result["dependencies"].values()) and "models" in result["ollama"] else 1


def worker(config, objective, profile="unified"):
    policy = Policy(config, approve)
    tools = Tools(policy, profile=profile)
    try:
        result = Agent(Ollama(config["model"]), tools, config["model"]).run(objective)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "reported" else 2
    except Stopped:
        print("Stopped. Inspect the workspace for partial changes.")
        return 130
    # Final CLI boundary: report arbitrary adapter failures with redaction, not a raw traceback.
    except Exception as exc:  # noqa: BLE001
        print(f"Blocked: {type(exc).__name__}: {redact(str(exc))}")
        return 1
    finally:
        tools.close()


def supervise(config_path, config, objective, profile="unified"):
    recover_execution(config)
    stop = Path(config["paths"]["state"]) / "STOP"
    if stop.exists():
        print("Stop latch is set. Review partial work, then run: python -m local_agent resume")
        return 130
    argv = [sys.executable, "-m", "local_agent", "--config", str(Path(config_path).resolve()),
            "_worker", objective, "--profile", profile]
    child = subprocess.Popen(argv)
    job = None
    if os.name == "nt":
        from .windows_job import WindowsJob
        try:
            job = WindowsJob(child)
        except OSError:
            child.kill()
            child.wait(timeout=5)
            raise RuntimeError("Cannot establish owned-process cancellation boundary; launch refused")
    try:
        while child.poll() is None:
            if stop.exists():
                raise KeyboardInterrupt
            time.sleep(0.1)
        return child.returncode
    except KeyboardInterrupt:
        stop.touch()
        if job:
            job.terminate()
        else:
            child.terminate()
        child.wait(timeout=10)
        print("Emergency stop: agent process tree terminated; completed actions cannot be undone.")
        return 130
    finally:
        if job:
            job.close()
        recover_execution(config, child.pid)


def main():
    parser = argparse.ArgumentParser(description="Local Windows AI agent")
    parser.add_argument("--config", default="agent.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "_worker"):
        command = sub.add_parser(name)
        command.add_argument("objective")
        command.add_argument("--profile", choices=list(PROFILES), default="unified")
    for name in ("doctor", "stop", "resume"):
        sub.add_parser(name)
    args = parser.parse_args()
    config = load(args.config)
    if args.command == "doctor":
        return doctor(config)
    if args.command == "stop":
        (Path(config["paths"]["state"]) / "STOP").touch()
        print("Stop requested; the supervisor will terminate its agent process tree.")
        return 0
    if args.command == "resume":
        (Path(config["paths"]["state"]) / "STOP").unlink(missing_ok=True)
        print("Stop latch cleared. No previous task has been restarted.")
        return 0
    if args.command == "_worker":
        return worker(config, args.objective, args.profile)
    return supervise(args.config, config, args.objective, args.profile)
