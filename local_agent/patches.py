"""Reviewed create/replace sets; checked per-file publication, never blind rollback."""
import difflib
import hashlib

from .file_ops import atomic_write
from .review import fingerprint, require_unchanged
from .safety import Denied, redact
from .verification import observe_artifact

MAX_FILES = 8
MAX_BYTES = 64_000
MAX_REVIEW = 32_000
FIELDS = frozenset({"path", "expected_sha256", "text"})


def validate_changes(changes):
    if type(changes) is not list or not 1 <= len(changes) <= MAX_FILES:
        raise TypeError("Patch changes must be a list of 1-8 objects")
    total = 0
    for item in changes:
        if (type(item) is not dict or set(item) != FIELDS
                or any(type(item[key]) is not str for key in FIELDS)):
            raise TypeError("Each change requires string path, expected_sha256 and text fields only")
        expected = item["expected_sha256"]
        if expected != "missing" and (len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected)):
            raise ValueError("expected_sha256 must be the raw-byte SHA-256 or 'missing' for a new file")
        total += len(item["text"].encode("utf-8"))
        if total > MAX_BYTES:
            raise ValueError("Patch proposed UTF-8 bytes exceed 64,000; split the change")


def apply(policy, changes):
    validate_changes(changes)
    proposals, reviews, seen = [], [], set()
    # Copy strings/bytes into private records before invoking the approval callback.
    for item in changes:
        path, text = item["path"], item["text"]
        target = policy.path(path, write=True)
        label = str(target.relative_to(policy.root))
        if target.is_relative_to(policy.state) or redact(label) != label:
            raise Denied("Patch cannot target private state or credential-pattern paths")
        if target in seen or any(target.is_relative_to(other) or other.is_relative_to(target) for other in seen):
            raise ValueError("Patch paths must be distinct and must not contain one another")
        seen.add(target)
        version = fingerprint(target, MAX_BYTES)
        expected = version[-1] if version else "missing"
        require_unchanged(item["expected_sha256"], expected)
        old = b""
        if version:
            with target.open("rb") as source:
                old = source.read(MAX_BYTES + 1)
            require_unchanged(version, fingerprint(target, MAX_BYTES))
            require_unchanged(version[-1], hashlib.sha256(old).hexdigest())
        before, raw = old.decode("utf-8"), text.encode("utf-8")
        changed = version is None or old != raw
        proposals.append((path, target, version, text, changed))
        if not changed:
            continue
        safe_before, safe_after = redact(before), redact(text)
        lines = difflib.unified_diff(safe_before.splitlines(True), safe_after.splitlines(True),
                                     fromfile=label if version else "/dev/null", tofile=label)
        diff = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)
        reviews.append({"path": label, "operation": "replace" if version else "create",
                        "expected_sha256": expected, "proposed_sha256": hashlib.sha256(raw).hexdigest(),
                        "proposed_bytes": len(raw), "diff": diff,
                        "redacted": before != safe_before or text != safe_after})
        if sum(len(row["diff"].encode("utf-8")) for row in reviews) > MAX_REVIEW:
            raise ValueError("Patch review exceeds 32,000 UTF-8 bytes; split the change")

    def check(items):
        for path, target, version, _, _ in items:
            require_unchanged(target, policy.path(path, write=True))
            require_unchanged(version, fingerprint(target, MAX_BYTES))

    check(proposals)
    if reviews:
        policy.confirm("apply_patch_set", {"files": reviews, "warning":
            "Publishes files sequentially, not as a crash-atomic transaction. Failure or stop may leave "
            "partial changes. No automatic rollback or retry. Redacted previews omit recognized secrets."})
    # An approval cannot authorize changed/deleted/recreated files or a new occupant.
    check(proposals)
    written, uncertain, observations = [], [], []

    def outcome(status, reason):
        return {"patch_status": status, "reason": reason, "written_paths": list(written),
                "uncertain_paths": list(uncertain), "verifications": list(observations),
                "pending_paths": [str(target.relative_to(policy.root)) for _, target, _, _, changed in proposals
                                  if changed and str(target.relative_to(policy.root)) not in written + uncertain]}

    for index, (path, target, version, text, changed) in enumerate(proposals):
        try:
            check(proposals[index:])
            if changed:
                uncertain.append(str(target.relative_to(policy.root)))
                atomic_write(policy, path, text, target, version)
                written.append(uncertain.pop())
            observation = observe_artifact(policy, path, text.encode("utf-8"), target)
            observations.append(observation)
            if observation["status"] != "passed":
                return outcome("incomplete", "Artifact readback did not pass; inspect changes before retrying")
        except (Denied, OSError, ValueError):
            return outcome("incomplete", "Resource conflict or inaccessible input; inspect changes before a fresh review"
                           if not uncertain else "Publication failed; inspect uncertain paths before a fresh review")
    return outcome("applied" if written else "no_changes", "Observed approved bytes; tests were not executed")
