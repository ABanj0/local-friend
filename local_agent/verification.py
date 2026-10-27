"""Test and artifact observations, independent of model prose and console summaries.

Approved repository code still runs as the host user. These records describe observations;
they are not hostile-process attestation or proof that the entire objective is complete.
"""
import hashlib
import json
import stat
import tempfile
import uuid
from pathlib import Path

from .process import run_process
from .review import fingerprint, require_unchanged
from .safety import Denied, redact

COUNTS = ("tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")
RUNNER = '''import json, os, sys, unittest
report_path, run_id = sys.argv[1:3]
# Ignore existing project bytecode, including same-size edits within one timestamp tick.
sys.pycache_prefix = os.path.join(os.path.dirname(report_path), "cache")
sys.dont_write_bytecode = True
sys.path.insert(0, os.getcwd())
class Recorder(unittest.TextTestRunner):
    def run(self, test):
        result = super().run(test)
        counts = dict(tests_run=result.testsRun, failures=len(result.failures),
                      errors=len(result.errors), skipped=len(result.skipped),
                      expected_failures=len(result.expectedFailures),
                      unexpected_successes=len(result.unexpectedSuccesses))
        with open(report_path, "x", encoding="utf-8") as report:
            json.dump(dict(schema=1, run_id=run_id, counts=counts), report)
        return result
program = unittest.main(module=None, argv=["unittest", *sys.argv[3:]],
                        testRunner=Recorder, exit=False)
raise SystemExit(0 if program.result.wasSuccessful() else 1)
'''


def assess(counts, exit_code):
    if exit_code != 0:
        return "failed", "process_failed"
    if counts is None:
        return "inconclusive", "no_structured_result"
    if any(counts[key] for key in ("failures", "errors", "unexpected_successes")):
        return "failed", "test_failures"
    if counts["tests_run"] == 0:
        return "failed", "zero_tests"
    if counts["skipped"] or counts["expected_failures"]:
        return "inconclusive", "not_all_tests_passed"
    return "passed", "nonzero_tests_passed"


def hex_value(value, length):
    return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)


def validate_artifact(record):
    if (type(record.get("version")) is not int or record.get("version") != 1
            or not hex_value(record.get("id"), 32) or not hex_value(record.get("expected_sha256"), 64)):
        raise ValueError("Invalid artifact verification identity")
    label = record.get("path")
    if (not isinstance(label, str) or not label or len(label) > 2048 or Path(label).is_absolute()
            or label.startswith(("/", "\\")) or ":" in label or ".." in Path(label).parts):
        raise ValueError("Invalid artifact label")
    expected = record.get("expected_bytes")
    size = record.get("observed_bytes")
    observation = record.get("observation")
    digest, resource = record.get("observed_sha256"), record.get("resource_version")
    if type(expected) is not int or not 0 <= expected <= 64000:
        raise ValueError("Invalid artifact byte count")
    if observation == "read":
        if (type(size) is not int or not 0 <= size <= 64000 or not hex_value(digest, 64)
                or not hex_value(resource, 64)):
            raise ValueError("Invalid artifact readback")
        matched = size == expected and digest == record["expected_sha256"]
        status, reason = ("passed", "content_matches") if matched else ("failed", "content_mismatch")
    elif observation in {"missing", "changed", "unreadable"} and size is None and digest is None and resource is None:
        status = "failed" if observation == "missing" else "inconclusive"
        reason = observation + "_artifact"
    else:
        raise ValueError("Invalid artifact observation")
    return {"id": record["id"], "kind": "artifact", "version": 1, "path": redact(label),
            "expected_bytes": expected, "expected_sha256": record["expected_sha256"],
            "observed_bytes": size, "observed_sha256": digest, "resource_version": resource,
            "observation": observation, "status": status, "reason": reason}


def observe_artifact(policy, path, expected, destination):
    """Read only the originally approved destination; never repair or replay a write."""
    if not destination.is_relative_to(policy.root):
        raise Denied("Artifact destination is outside the approved workspace")
    result = {"id": uuid.uuid4().hex, "kind": "artifact", "version": 1,
              "path": redact(str(destination.relative_to(policy.root)))[:2048],
              "expected_bytes": len(expected), "expected_sha256": hashlib.sha256(expected).hexdigest(),
              "observed_bytes": None, "observed_sha256": None, "resource_version": None}
    try:
        current = policy.path(path, write=True)  # Strict link/reparse/hardlink checks apply to readback too.
        require_unchanged(str(destination), str(current))
        version = fingerprint(current, 64000)
        if version is None:
            result["observation"] = "missing"
        else:
            require_unchanged(current, policy.path(path, write=True))
            require_unchanged(version, fingerprint(current, 64000))
            result.update(observation="read", observed_bytes=version[-3], observed_sha256=version[-1],
                          resource_version=hashlib.sha256(json.dumps(version[1:-1]).encode()).hexdigest())
    except Denied:
        result["observation"] = "changed"
    except OSError:
        result["observation"] = "unreadable"
    return validate_artifact(result)


def validate(record):
    """Only fixed fields/counts can become durable verification evidence."""
    if isinstance(record, dict) and record.get("kind") == "artifact":
        return validate_artifact(record)
    if (not isinstance(record, dict) or record.get("kind") != "unittest" or type(record.get("version")) is not int
            or record.get("version") != 1
            or type(record.get("exit_code")) is not int or record.get("profile") != "test"):
        raise ValueError("Invalid test verification record")
    ident = record.get("id")
    digest = record.get("command_sha256")
    if (not isinstance(ident, str) or len(ident) != 32 or any(c not in "0123456789abcdef" for c in ident)
            or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
        raise ValueError("Invalid verification identity")
    counts = record.get("counts")
    if counts is not None and (not isinstance(counts, dict) or set(counts) != set(COUNTS) or
                               any(type(value) is not int or not 0 <= value <= 1_000_000 for value in counts.values())):
        raise ValueError("Invalid test counts")
    status, reason = assess(counts, record["exit_code"])
    return {"id": ident, "kind": "unittest", "version": 1, "profile": "test",
            "command_sha256": digest, "exit_code": record["exit_code"], "counts": counts,
            "status": status, "reason": reason}


def command(argv, directory, policy, *, instrument, on_output=None):
    ident = uuid.uuid4().hex
    digest = hashlib.sha256(json.dumps(argv).encode()).hexdigest()
    counts = None
    with tempfile.TemporaryDirectory(prefix="test-verification-", dir=policy.state) as temporary:
        script, report = Path(temporary) / "runner.py", Path(temporary) / "result.json"
        if instrument:
            script.write_text(RUNNER, encoding="utf-8")
            version = fingerprint(script, 64000)
            execution = [argv[0], str(script), str(report), ident, *argv[3:]]
        else:
            execution = argv
        details = {"argv": execution, "cwd": str(directory),
                   "warning": "Repository code runs with your Windows user permissions."}
        if instrument:
            details.update(requested_argv=argv, verifier="unittest counts v1",
                           runner_sha256=hashlib.sha256(RUNNER.encode()).hexdigest())
        policy.confirm("execute_code", details)
        if instrument:
            require_unchanged(version, fingerprint(script, 64000))
        outcome = run_process(execution, directory, policy, on_output=on_output)
        if instrument:
            try:
                for path in (Path(temporary), report):
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                        raise Denied("Verification report paths cannot be links")
                expected = fingerprint(report, 4096)
                with report.open("rb") as stream:
                    raw = stream.read(4097)
                if len(raw) > 4096:
                    raise ValueError("Verification report exceeds its byte limit")
                payload = json.loads(raw)
                require_unchanged(expected, fingerprint(report, 4096))
                if type(payload.get("schema")) is int and payload.get("schema") == 1 and payload.get("run_id") == ident:
                    candidate = payload.get("counts")
                    validate({"id": ident, "kind": "unittest", "version": 1, "profile": "test",
                              "command_sha256": digest, "exit_code": outcome["exit_code"], "counts": candidate})
                    counts = candidate
            except (OSError, Denied, ValueError, TypeError, AttributeError):
                pass  # No raw malformed report data enters logs or persistence.
    outcome["verification"] = validate({"id": ident, "kind": "unittest", "version": 1, "profile": "test",
                                        "command_sha256": digest, "exit_code": outcome["exit_code"], "counts": counts})
    return outcome
