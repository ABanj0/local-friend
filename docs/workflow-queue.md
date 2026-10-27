# Durable workflow admission leases

P2-03 A0 provides private queue primitives for selected-file, read-only inspections.
This document describes that prerequisite's boundary. A1 now integrates a runtime-only
timer and authenticated controls; see [scheduled inspections](interval-inspections.md).
The queue remains private and is not a model tool or unrestricted execution endpoint.

## Admission and recovery

A trusted coordinator supplies a stable 64-character hexadecimal trigger key. Repeating
that key with the exact retained request and conversation returns the same item, including
cancelled or admitted items. Rebinding a key to different work is rejected. Requests bind
the database identity, project directory identity, literal selected paths, model name and
validated inference options. File contents and model identity are checked afresh when a
task is admitted; enqueueing does not freeze file versions.

Claims last 1–30 seconds (15 by default). Only a token hash is stored; the nonce stays
private to its owner. Expired or replaced claims cannot admit work. Expiry uses UTC
milliseconds, so system-clock adjustments can affect lease duration.

One SQLite transaction creates the task, initial inspection checkpoint and queue-to-task
association. An admitted item is never automatically requeued, even if the commit reply
is lost, the runtime crashes or its task history is subsequently removed. This guarantees
at most one retained task admission per trigger, not exactly one execution. A crash after
admission but before worker startup can leave an interrupted task that never ran.

## Limits and permissions

Only current owned claims can be released for a known pre-admission resource conflict.
Pending items can be cancelled even while STOP is latched. Normal manager ownership,
scope, busy, shutdown and stop guards still apply. A1 must integrate dispatcher lifecycle
and emergency-stop controls before enabling automatic work.

Storage is bounded to 1,000 retained items, 64 KiB per payload and 64 MiB total payloads;
one claim attempt scans at most 32 candidates. Malformed or restored-identity requests
are blocked without exposing their contents. Receipts remain until their conversation
is deleted. Pending work protects conversations from bulk retention; cross-conversation
queue/task links prevent retention. Queue content is private, unencrypted backup data.
These controls do not provide operating-system isolation.

## Verification

Run `python -m unittest tests.test_work_queue tests.test_migrations -v`. Tests cover real
SQLite concurrency, process crashes, lost acknowledgements and supervised worker reads.
Inference uses an explicit protocol fixture. Packaged runtime regressions do not establish
an unimplemented scheduling UI or actual-model quality.

SQLite documents the underlying [transaction](https://www.sqlite.org/lang_transaction.html)
and [atomic commit](https://www.sqlite.org/atomiccommit.html) behavior.
