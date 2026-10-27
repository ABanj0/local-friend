# Execution journal and recovery

In Studio, open **Task history → Execution journal and recovery → Load execution
journal**. Each numbered decision shows its tool operations and effect class. Decision
numbers describe executor iterations, rather than promises that the model followed every
line of its proposed plan.

## Understand the states

- **Intent committed:** the parent stored the operation before acknowledging dispatch.
- **Result observed:** the parent stored the returned outcome. Check verifier references
  and the task report separately; this state does not certify task success.
- **Interrupted:** a decision or observational operation ended without a completed result.
- **Unknown:** a potentially mutating operation has an intent without a committed result.
  It might have changed files, started a process, or affected a browser/application.

Worker exit, cancellation, supervision failure and backend restart reconcile pending work
into these states. Committed results remain completed even when their containing decision
was interrupted. No action is replayed. A crash after an external effect but before storing
its result cannot establish exactly-once execution.

## Inspect and reconcile

For file writes and patch sets, expand **Recorded artifact preconditions** to see bounded
preimage/proposed SHA-256 observations. **Inspect current artifacts** performs a fresh
read within the currently configured workspace and the recorded project directory.
It compares the current file with its recorded identity/version and proposed bytes.

Inspection never writes files, runs commands, grants approval, changes an unknown outcome
to completed, or retries an operation. Matching bytes do not establish who wrote them.
Review current artifacts and any external application manually before deciding what is
safe next. Other tool categories have effect classes and result evidence, without invented
filesystem preconditions or restored browser/window handles.

Choose **Write a new instruction** to open the original conversation and describe the
next action. This only opens the composer. It preserves an existing draft and does not
resubmit the old objective, reuse approvals, or restore executor state. Each submitted run
receives new operation IDs and normal scope/approval checks. Pause/checkpoint resume
remains unavailable.

## Bounds and security

The authenticated endpoints are `GET /tasks/{task}/journal` and
`GET /tasks/{task}/journal/{operation}/inspect`. They have no execution/replay counterpart.
The journal admits at most 128 decisions, 256 operations and eight artifact preconditions
per operation, with 64,000-byte fingerprint limits. Malformed persisted observations are
omitted with a partial-journal notice. Missing, oversized, redacted, credential, symlink,
hardlink, relocated/recreated project, and emergency-stop cases can make comparisons
unavailable. No file contents, command arguments or approval bodies are added to journal
rows. Argument hashes identify observations; they never authorize execution.

Every explicit Studio tool dispatch requires the parent's committed-intent acknowledgement.
Failure or mismatch stops dispatch; a result acknowledgement is required before the next
model action. Mandatory owned-process/browser cleanup still runs after journal failures.
This journal is not an operating-system sandbox. The terminal CLI retains its existing
audit log; durable Studio recovery is not claimed for standalone CLI tasks.

## Database upgrades

SQLite schema versions 1 and 2 adopt the existing store and add the operation journal.
Migration history and `PRAGMA user_version` advance in one transaction; failure rolls back.
Existing conversations, metrics, goals, attachments, store identity and event cursors are
preserved. Older tasks remain available with an explicit “no operation journal” notice;
their missing evidence is not reconstructed.

Future schema versions or inconsistent history fail startup rather than being silently
repaired. Use the compatible application version and retain the database for diagnosis.
Before manually copying state, stop the owning backend cleanly; never delete the database
or copy only its main file while WAL writes are active. This increment adds no automatic
backup/restore UI or rollback-to-old-application guarantee.

## Verification

Run `python -m unittest tests.test_migrations tests.test_journal -v` in the project venv.
Real spawned-worker tests exit before intent, during execution, after effect and after
result commit, and assert no replay. Storage/acknowledgement failures, stale preconditions,
approval freshness, API authentication and data preservation have separate regressions.
The real-model test requires `LOCAL_AGENT_MODEL_TEST=1`; rendered Edge tests require
`LIVE_STUDIO_UI=1`. Defaults report these as skipped. See `IMPLEMENTATION.md` for the
actual source/frozen and Ollama results, plus remaining native packaging limitations.
