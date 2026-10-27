# Artifact readback evidence

`write_file` now performs a bounded readback after publication, and for requests that
already match an existing file. It compares the observed bytes and SHA-256 with the
proposed UTF-8 content. Exact line endings are preserved: changing CRLF to LF is a real
overwrite that requires review rather than silently passing as a no-op.

Studio displays an **Artifact readback** card independently of the model's report.
The authenticated `GET /tasks/{id}/verifications` returns artifact and test observations
from the same durable history. Records survive restart and are removed with their chat.

| Observation | Meaning |
| --- | --- |
| `passed` | A stable read of the approved destination matched proposed byte count and hash |
| `failed` | The destination was missing or its content differed |
| `inconclusive` | Readback was unreadable, unstable, or refused by link/path protections |

Approval and atomic-write boundaries remain in force. Readback rechecks the originally
approved destination, refuses symlink/reparse/hardlink inputs and hashes at most 64,000
bytes. A no-op observation does not rewrite the file. If another process changes or
removes a file after publication, the verifier records the problem without restoring
bytes, retrying a mutation or reusing an approval.

Evidence contains a fresh ID, version, sanitized relative file label, expected/observed
byte counts and content hashes, plus an opaque version digest of the observed file's
identity/metadata. File contents and raw filesystem errors are not copied into it.
Labels are bounded and use the existing best-effort credential-pattern redaction.
The parent validates fixed fields and recomputes the verdict before persistence;
model-provided prose cannot insert a verification event or override mismatched hashes.

This is a point-in-time observation of bytes at an approved path. It does not establish
that the code is correct, certify the whole objective, monitor later changes, or authorize
a future write. Tests remain separately necessary. Resource-version invalidation and
durable workflow reconciliation are later roadmap work. Trusted-host execution is not
OS isolation or attestation against a malicious process with the same user permissions.

The initial artifact verifier applies to coding writes and no-ops. It does not automatically
certify arbitrary downloads, native screenshots, user-specified external paths or files
that were never observed. Existing model/native/installer acceptance gates remain separate.
