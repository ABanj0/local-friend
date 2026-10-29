"""Bounded process execution; never runs a shell or accepts arbitrary command strings."""
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

from .command_output import MAX_PARTS, CommandOutput, OutputPublisher
from .safety import Stopped


def environment():
    env = {key: value for key, value in os.environ.items() if key.upper() in {
        "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "COMSPEC",
    }}
    env.update(PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull)
    return env


def terminate_tree(proc):
    if proc.poll() is None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)


def run_process(argv, cwd, policy, timeout=60, *, on_output=None, raw_output=False, stdin=None, windows_ssh=False):
    if raw_output and on_output is not None:
        raise ValueError("Internal raw command parsing cannot use an output stream")
    policy.check_stop()
    env = environment()
    if windows_ssh:
        expected = Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/OpenSSH/ssh.exe"
        if os.name != "nt" or Path(argv[0]).resolve() != expected.resolve():
            raise ValueError("Windows SSH environment is restricted to the fixed OS transport client")
        # Windows OpenSSH requires this OS directory even with explicit keys/config.
        # It is client metadata, never forwarded to the guest or repository processes.
        env.update({key: value for key, value in os.environ.items() if key.upper() == "PROGRAMDATA"})
    output, ident = CommandOutput(sanitize=not raw_output), uuid.uuid4().hex
    proc = subprocess.Popen(argv, cwd=Path(cwd), env=env, stdin=subprocess.DEVNULL if stdin is None else stdin,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    job, reader = None, None
    publisher = OutputPublisher(output, on_output, ident, max_parts=MAX_PARTS)
    reason = "failed"

    try:
        if os.name == "nt":
            from .windows_job import WindowsJob
            job = WindowsJob(proc)
        reader = threading.Thread(target=output.drain, args=(proc.stdout,), daemon=True)
        reader.start()
        publisher.publish()
        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            policy.check_stop()
            if time.monotonic() > deadline:
                reason = "timeout"
                raise TimeoutError("Command exceeded its time budget")
            publisher.publish()
            time.sleep(.05)
        reason = "completed"
    except Stopped:
        reason = "cancelled"
        raise
    finally:
        try:
            if job:
                job.close()  # Also closes descendants that inherited the output pipe.
            terminate_tree(proc)
            if reader and reader.ident is not None:
                reader.join(2)
                if reader.is_alive():
                    reason = "output_error"
                    raise OSError("Owned command output did not close after process shutdown")
            else:
                proc.stdout.close()
            if output.failed:
                reason = "output_error"
                raise OSError("Owned command output could not be read")
        finally:
            publisher.publish(reason, final=True, exit_code=proc.poll())
    text, truncated = output.snapshot()
    return {"exit_code": proc.returncode, "output": text, "truncated": truncated, "command_id": ident}
