"""Task-owned background commands with bounded output and explicit local readiness."""
import http.client
import math
import os
import socket
import subprocess
import threading
import time
import uuid
from urllib.parse import urlsplit

from .command_output import CommandOutput, OutputPublisher
from .process import environment, terminate_tree
from .safety import Stopped, redact


def readiness_config(config):
    if config is None:
        return None
    if not isinstance(config, dict) or not {"url"} <= config.keys() <= {"url", "status", "timeout", "interval"}:
        raise ValueError("Readiness requires a trusted url and optional status/timeout/interval")
    url = config["url"]
    if (not isinstance(url, str) or len(url) > 512 or not url.isascii()
            or any(ord(char) < 33 or ord(char) == 127 for char in url)
            or redact(url) != url):
        raise ValueError("Readiness URL must be bounded and contain no credentials/control characters")
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"} or not parsed.port
            or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError("Readiness allows only literal loopback HTTP with an explicit port, no credentials/query/fragment")
    status, timeout, interval = config.get("status", 200), config.get("timeout", 10), config.get("interval", .2)
    if (type(status) is not int or not 200 <= status < 300
            or type(timeout) not in {int, float} or not math.isfinite(timeout) or not .1 <= timeout <= 30
            or type(interval) not in {int, float} or not math.isfinite(interval) or not .05 <= interval <= 2):
        raise ValueError("Readiness requires a 2xx status, 0.1-30s timeout and 0.05-2s interval")
    # Check the optional dependency before approval/spawn, never silently skip ownership.
    try:
        import psutil  # noqa: F401
    except ImportError:
        raise ValueError("Readiness ownership checks need psutil; install the project's desktop extra") from None
    return {"url": url, "host": parsed.hostname, "port": parsed.port, "path": parsed.path or "/",
            "status": status, "timeout": timeout, "interval": interval}


def accept_status(payload, commands, settings, streams, updates):
    if not isinstance(payload, dict) or set(payload) != {"command_id", "profile", "pid", "state", "readiness"}:
        raise ValueError("Invalid background status fields")
    ident, profile, pid = payload["command_id"], payload["profile"], payload["pid"]
    if (not isinstance(ident, str) or ident not in streams or not isinstance(profile, str) or profile not in commands
            or streams[ident][3] != profile or type(pid) is not int or pid <= 0
            or not isinstance(payload["state"], str) or payload["state"] not in {"starting", "running", "exited", "stopped", "failed"}):
        raise ValueError("Invalid background status identity")
    ready = payload["readiness"]
    if (not isinstance(ready, dict) or set(ready) != {"status", "url", "status_code", "checked_at", "last_ready_at", "last_check"}
            or not isinstance(ready["status"], str) or ready["status"] not in {"starting", "unconfigured", "ready", "unready", "ownership_unverified", "timeout", "exited", "stopped"}
            or ready["url"] != (settings["url"] if settings else None)
            or ready["status_code"] is not None and (type(ready["status_code"]) is not int or not 100 <= ready["status_code"] <= 599)):
        raise ValueError("Invalid background readiness observation")
    if ready["last_check"] is not None and (not isinstance(ready["last_check"], str)
            or ready["last_check"] not in {"ready", "unready", "ownership_unverified"}):
        raise ValueError("Invalid readiness check result")
    for key in ("checked_at", "last_ready_at"):
        stamp = ready[key]
        if stamp is not None and (type(stamp) not in {int, float} or not math.isfinite(stamp) or not 0 <= stamp <= time.time() + 60):
            raise ValueError("Invalid readiness timestamp")
    if ready["status"] == "ready" and (not settings or ready["status_code"] != settings["status"]
            or ready["last_ready_at"] is None or ready["checked_at"] is None):
        raise ValueError("Readiness requires an observed configured status")
    count, previous_pid = updates.get(ident, (0, pid))
    if count >= 256 or previous_pid != pid:
        raise ValueError("Background status update limit or identity changed")
    updates[ident] = (count + 1, pid)


class BackgroundCommand:
    def __init__(self, policy, profile, argv, directory, settings, output=None, status=None):
        self.policy, self.profile, self.argv, self.directory = policy, profile, argv, directory
        self.settings, self.status_sink = settings, status
        self.ident = uuid.uuid4().hex
        self.capture = CommandOutput()
        self.publisher = OutputPublisher(self.capture, output, self.ident)
        self.proc = self.job = self.reader = self.monitor = None
        self.lock, self.probe_lock = threading.RLock(), threading.Lock()
        self.stop_requested, self.ready = threading.Event(), threading.Event()
        self.state, self.failure = "starting", None
        self.readiness = {"status": "starting" if settings else "unconfigured", "url": settings["url"] if settings else None,
                          "status_code": None, "checked_at": None, "last_ready_at": None, "last_check": None}
        self.delivery_failed = False
        self.resources_closed = False
        self.status_updates = 0

    def snapshot(self):
        with self.lock:
            text, truncated = self.capture.snapshot()
            return {"profile": self.profile, "command_id": self.ident, "pid": self.proc.pid if self.proc else None,
                    "state": self.state, "process_exit_code": self.proc.poll() if self.proc else None,
                    "readiness": dict(self.readiness), "output": text, "truncated": truncated,
                    "error": self.failure}

    def emit_status(self):
        if self.status_sink and not self.delivery_failed and self.status_updates < 256:
            current = self.snapshot()
            payload = {key: current[key] for key in ("profile", "command_id", "pid", "state", "readiness")}
            try:
                self.status_sink(payload)
                self.status_updates += 1
            except BaseException:
                self.delivery_failed = True
                raise

    def start(self):
        self.policy.check_stop()
        self.proc = subprocess.Popen(self.argv, cwd=self.directory, env=environment(), stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            if os.name == "nt":
                from .windows_job import WindowsJob
                self.job = WindowsJob(self.proc)
            self.reader = threading.Thread(target=self.capture.drain, args=(self.proc.stdout,), daemon=True)
            self.reader.start()
            self.state = "running"
            self.publisher.publish()
            self.emit_status()
            self.monitor = threading.Thread(target=self.run, daemon=True)
            self.monitor.start()
        except BaseException:
            self.state, self.failure = "failed", "Background startup failed"
            self.cleanup("failed")
            raise

    def probe(self):
        """Never contact a listener unless all listeners on that port are task-owned."""
        import psutil

        with self.probe_lock:
            status, code = "ownership_unverified", None
            try:
                parent = psutil.Process(self.proc.pid)
                owners = {parent.pid, *(child.pid for child in parent.children(recursive=True))}
                listeners = [connection for connection in psutil.net_connections(kind="tcp")
                             if connection.status == psutil.CONN_LISTEN and connection.laddr
                             and connection.laddr.port == self.settings["port"]]
                if self.proc.poll() is None and listeners and all(connection.pid in owners for connection in listeners):
                    connection = http.client.HTTPConnection(self.settings["host"], self.settings["port"], timeout=.3)

                    def interrupt():
                        endpoint = connection.sock
                        if endpoint is not None:
                            try:
                                endpoint.shutdown(socket.SHUT_RDWR)
                            except OSError:
                                pass

                    # Socket timeouts reset on each read; bound header trickling too.
                    watchdog = threading.Timer(.35, interrupt)
                    watchdog.daemon = True
                    try:
                        watchdog.start()
                        connection.request("GET", self.settings["path"], headers={"Connection": "close"})
                        with connection.getresponse() as response:
                            code = response.status  # No redirect, body read, cookie, proxy or credentials.
                        status = "ready" if code == self.settings["status"] else "unready"
                    finally:
                        watchdog.cancel()
                        if watchdog.ident is not None:
                            watchdog.join(.5)
                        connection.close()
            except psutil.Error:
                status = "ownership_unverified"
            except (OSError, http.client.HTTPException):
                status = "unready"
            with self.lock:
                if self.state != "running":
                    return
                stamp = time.time()
                self.readiness.update(status=status, last_check=status, status_code=code, checked_at=stamp)
                if status == "ready":
                    self.readiness["last_ready_at"] = stamp
            return status

    def run(self):
        deadline = time.monotonic() + (self.settings["timeout"] if self.settings else 0)
        last_probe = 0
        reason = "completed"
        try:
            while not self.stop_requested.is_set() and self.proc.poll() is None:
                self.policy.check_stop()
                self.publisher.publish()
                if self.settings and not self.ready.is_set():
                    if time.monotonic() - last_probe >= self.settings["interval"]:
                        state = self.probe()
                        last_probe = time.monotonic()
                        if state == "ready" and time.monotonic() < deadline:
                            self.emit_status()
                            self.ready.set()
                    if not self.ready.is_set() and time.monotonic() >= deadline:
                        self.readiness["status"] = "timeout"
                        self.failure = "Configured readiness did not pass before its deadline"
                        self.state, reason = "failed", "timeout"
                        break
                self.stop_requested.wait(.05)
            if self.stop_requested.is_set():
                self.state, reason = "stopped", "cancelled"
            elif self.state != "failed":
                self.state = "exited"
                if self.settings:
                    self.readiness["status"] = "exited"
                    if self.readiness["last_ready_at"] is None:
                        self.failure = "Process exited before configured readiness passed"
        except Stopped:
            self.state, reason = "stopped", "cancelled"
        except Exception:  # noqa: BLE001 -- thread boundary: never log raw process/network errors
            self.state, self.failure, reason = "failed", "Background observation failed", "failed"
        finally:
            try:
                self.cleanup(reason)
            except Exception:  # noqa: BLE001 -- surface cleanup failure in owned status, not a thread traceback
                self.state, self.failure = "failed", "Owned background cleanup needs attention"
            self.ready.set()

    def cleanup(self, reason):
        try:
            if self.job:
                self.job.close()
                self.job = None
        finally:
            if self.proc:
                terminate_tree(self.proc)
        if self.proc:
            if self.reader and self.reader.ident is not None:
                self.reader.join(2)
                if self.reader.is_alive():
                    raise OSError("Owned background output did not close")
            else:
                self.proc.stdout.close()
            if self.capture.failed:
                self.state, self.failure, reason = "failed", "Background output could not be read", "output_error"
            self.resources_closed = True
            if self.state == "stopped":
                self.readiness["status"] = "stopped"
            self.publisher.publish(reason, final=True, exit_code=self.proc.poll())
        self.emit_status()

    def wait_ready(self):
        if self.settings:
            while not self.ready.wait(.05):
                self.policy.check_stop()
        self.policy.check_stop()
        return self.snapshot()

    def status(self):
        self.policy.check_stop()
        if self.settings and self.state == "running" and self.proc.poll() is None:
            self.probe()
            self.emit_status()
        return self.snapshot()

    def stop(self):
        self.stop_requested.set()
        if self.monitor and self.monitor.ident is not None:
            self.monitor.join(3)
            if self.monitor.is_alive():
                raise OSError("Owned background monitor did not stop")
        if not self.resources_closed:
            self.cleanup("failed")
        return self.snapshot()
