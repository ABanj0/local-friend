"""Development-only native preflight. No agent tool, privileged HTTP API or UI certification."""
import argparse
import json
import os
import re
import socket
import stat
import threading
import time
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .studio.process_output import ProcessOutput

MAX_LOG = 1024 * 1024
MAX_REPORT = 8192
EXE = Path("desktop/src-tauri/target/debug/local-agent-studio.exe")
PAGE = b"<!doctype html><title>Native diagnostic</title><p>Native diagnostic only. Close this window after the check.</p>"


def classify(text, *, truncated=False):
    if truncated:
        text = text.rsplit("\n", 1)[0] if "\n" in text else ""
    codes = []
    for match in re.finditer(r"GPU process exited unexpectedly: exit_code=(-?\d{1,11})(?=\s|$)", text):
        value = int(match[1])
        if -(2**31) <= value < 2**31 and value not in codes and len(codes) < 8:
            codes.append(value)
    return {"gpu_exit_codes": [{"signed": value, "hex": f"0x{value & 0xffffffff:08x}"}
                               for value in codes],
            "gpu_access_denied": -1073741790 in codes,
            "gpu_unusable": "GPU process isn't usable. Goodbye." in text,
            "input_truncated": truncated}


def no_links(root, target):
    if not target.is_relative_to(root):
        raise ValueError("Diagnostic path is outside the checkout")
    current = root
    for part in ("", *target.relative_to(root).parts):
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Diagnostic paths cannot contain links")


def consume_log(root, path):
    """Read only the expected owned regular log, export categories, remove that exact file."""
    no_links(root, path)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return classify("") | {"log_present": False, "raw_log_removed": False}
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError("Diagnostic log is not a single-link regular file")

    def identity(info):
        return info.st_dev, info.st_ino, info.st_nlink, info.st_size, info.st_mtime_ns

    with path.open("rb") as stream:
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError("Diagnostic log changed")
        raw = stream.read(MAX_LOG + 1)
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError("Diagnostic log changed")
    no_links(root, path)
    if identity(path.lstat()) != identity(before):
        raise ValueError("Diagnostic log changed")
    result = classify(raw[:MAX_LOG].decode("utf-8", errors="replace"),
                      truncated=len(raw) > MAX_LOG)
    path.unlink()  # Only this captured file; browser profile/unknown files are preserved.
    return result | {"log_present": True, "raw_log_removed": True}


class ProbeServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, port=1420):
        self.requested = threading.Event()
        self._timers = {}
        super().__init__(("127.0.0.1", port), ProbeHandler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(.25)
        # A per-read timeout alone can be extended forever by dripping headers.
        def expire():
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        timer = threading.Timer(.5, expire)
        timer.daemon = True
        self._timers[connection] = timer
        timer.start()
        return connection, address

    def close_request(self, connection):
        timer = self._timers.pop(connection, None)
        if timer:
            timer.cancel()
        super().close_request(connection)

    def handle_error(self, request, client_address):
        pass  # Closed/cancelled probes must not print raw request/exception contents.


class ProbeHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        self.server.requested.set()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(PAGE)


def existing_studio():
    import psutil
    return any(p.info["name"] in {"local-agent-studio.exe", "local_agent_studio.exe"}
               for p in psutil.process_iter(["name"]))


def listening(port):
    with socket.socket() as connection:
        connection.settimeout(.2)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def diagnose(root, seconds=10):
    if type(seconds) is not int or not 1 <= seconds <= 30:
        raise ValueError("Diagnostic duration must be an integer from 1 to 30 seconds")
    root = Path(root).resolve()
    marker = root / "desktop/src-tauri/Cargo.toml"
    no_links(root, marker)
    if not marker.is_file():
        raise ValueError("Run native diagnostics from the development checkout")
    case = root / ".runtime" / ("native-diagnostic-" + uuid.uuid4().hex)
    no_links(root, case)
    case.mkdir(parents=True)  # Exclusive new case; preserve all existing cases.
    report = {"version": 1, "scope": "native_preflight_only", "status": "blocked",
              "native_acceptance": "not_verified", "reason": None,
              "observations": classify(""), "native_exit_code": None,
              "native_launched": False, "native_pid": None,
              "started_utc": datetime.now(UTC).isoformat(),
              "frontend_requested": False, "owned_closed": True,
              "profile_retained": True, "seconds_limit": seconds}
    service, server, thread = ProcessOutput(), None, None
    log = case / "webview.log"
    try:
        executable = root / EXE
        no_links(root, executable)
        if not executable.is_file():
            report["reason"] = "missing_native_debug_build"
        elif existing_studio():
            report["reason"] = "existing_studio_preserved"
        elif listening(17861):
            report["reason"] = "existing_backend_preserved"
        else:
            try:
                server = ProbeServer()
            except OSError:
                report["reason"] = "frontend_port_unavailable"
            else:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                env = dict(os.environ)
                env["WEBVIEW2_USER_DATA_FOLDER"] = str(case / "webview")
                inherited = env.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
                # Logging only. No GPU, sandbox, origin, permission or desktop override.
                env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
                    inherited + ' --enable-logging --log-file="' + str(log) + '"').strip()
                report["inherited_browser_arguments"] = bool(inherited)
                service.start([str(executable)], env)
                report["native_launched"], report["native_pid"] = True, service.proc.pid
                report["owned_closed"] = False
                report["status"] = "inconclusive"
                deadline = time.monotonic() + seconds
                while service.proc.poll() is None and time.monotonic() < deadline:
                    no_links(root, log)
                    if log.exists() and log.stat().st_size > MAX_LOG:
                        report["status"], report["reason"] = "blocked", "log_capture_limit"
                        break
                    time.sleep(.05)
                report["native_exit_code"] = service.proc.poll()
                report["frontend_requested"] = server.requested.is_set()
    except Exception:  # noqa: BLE001 -- no raw exception, environment or log bodies in reports
        report["status"], report["reason"] = "blocked", "diagnostic_failed"
    finally:
        try:
            service.close()
            report["owned_closed"] = service.proc is None or service.proc.poll() is not None
        except Exception:  # noqa: BLE001 -- preserve other cleanup even on an OS failure
            report["owned_closed"] = False
            report["status"], report["reason"] = "blocked", "owned_cleanup_failed"
        finally:
            if server:
                if thread and thread.ident is not None:
                    server.shutdown()
                    thread.join(2)
                server.server_close()
    try:
        report["observations"] = consume_log(root, log)
    except (OSError, ValueError):
        report["status"], report["reason"] = "blocked", "log_changed_or_unreadable_preserved"
    if report["status"] != "blocked":
        if report["observations"]["gpu_unusable"] or report["native_exit_code"] not in (None, 0):
            report["status"], report["reason"] = "observed_failure", "native_startup_failure"
        elif report["frontend_requested"]:
            report["status"] = "frontend_requested"
    data = json.dumps(report, indent=2) + "\n"
    if len(data.encode()) > MAX_REPORT:
        raise ValueError("Diagnostic report exceeded its fixed output budget")
    target = case / "report.json"
    no_links(root, target)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(data)
    return report, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=10)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    report, path = diagnose(root, args.seconds)
    print(json.dumps({"report": str(path.relative_to(root)), **report}))
    return 0 if report["status"] == "frontend_requested" else 1


if __name__ == "__main__":
    raise SystemExit(main())
