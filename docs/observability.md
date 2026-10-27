# Run diagnostics

Open **Task history → Run diagnostics → Load diagnostics** in Studio. Inspect timing,
outcomes, verifier observations and spans, then **Download diagnostic JSON**.
The authenticated API is `GET /tasks/<task-id>/diagnostics`. It is read-only and never
repeats actions. Existing locality/token/origin checks apply.

## Correlation and outcomes

The task UUID is the run ID. Versioned spans identify worker run, planning, model calls,
decision iterations, tool attempts, approvals and cleanup. Start/result/approval events
share run/step/call references; tool spans link independently persisted verifier IDs.
Decision iterations do not assert prose-plan completion. These records are not execution
authority, an intent journal, a checkpoint or permission to replay.

Taxonomy distinguishes observed execution, denial, invalid input, timeout, transport/error,
execution failure, failed verification and inconclusive verification. `reported` remains
a reporting state; whole-task certification is **not assessed**. Prose cannot override
failed/zero-test evidence. Unfinished spans have unknown duration and become interrupted
observations after the task ends.

## Timing and counters

Worker wall time includes cleanup; model wall time covers the observed request/load/prompt/
generation wait. Tool-active time excludes the union of approval intervals; nested waits
count once. Cleanup/other time are separate; plan wall time is inclusive, not additive.
Differences use [Python's monotonic performance counter](https://docs.python.org/3.12/library/time.html#time.perf_counter_ns).
They include instrumentation/transport and omit pre-worker admission/spawn. They are not
CPU/GPU utilization or native Ollama stage timings.

Existing Ollama final-response counters supply tokens, generation speed and measured call
count. They are not parsed from prose or counted again from spans. Aborted/legacy runs
can lack counters. Partial completed-span totals are lower bounds. Corpus quality,
repeat measurements and p50/p95 remain P1-08 B, with no achieved score claimed here.

## Privacy, bounds and recovery

Export allows IDs, fixed categories, numeric observations, hashes and verifier links.
It excludes chat/title/model-name/URL/path/argument/output/diff/image/approval/environment
contents and raw errors. Identifier/requested-setting hashes support comparison without
source text; they are not weights digests or applied-setting proof. Exact launch credentials
are removed even on identifier collision.

At most 512 spans/1,024 events are emitted; further spans are counted as dropped while
execution continues. Reads bound rows/payloads and export at most 200 verifier summaries.
Missing, malformed, capped and interrupted data is partial. Old runs have no invented
timings. SQLite uses a consistent snapshot and task/kind index; existing deletion removes
its records. Storage failures use the existing supervisor boundary. No hostile-code
attestation, resume state, cloud telemetry, framework or dependency is introduced.

Studio workers/shortcuts are covered; standalone CLI keeps its existing audit path.
Old binaries require rebuilding. Native WebView/installer and current real-model gates
remain separate. Run `python -m unittest tests.test_observability -v`. Enable
`LIVE_STUDIO_UI=1` for `tests.test_tool_profile_ui`: real worker/backend/history/download
paths use explicit model protocol fixtures, not a local-model quality benchmark.
