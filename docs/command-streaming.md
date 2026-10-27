# Live command output

Approved foreground test/lint/build commands now display **Command output** in Studio's
activity panel while they run. `/test` uses the same path. The panel shows recent commands
and active owned servers for the selected conversation, their profile, plain-text output and
observed exit/interrupt status. Select a conversation after reopening Studio to inspect its
retained output. Existing single-action execute-code approval is still required.

Output is not test verification. A process can exit zero without running tests; the
separate **Test run** observation still checks structured unittest counts. Unsupported
frameworks, cancellation and absent results do not become passing tests.

## Bounds and retention

- stdout/stderr merge into one pipe. A reader drains the process continuously; foreground
  output no longer grows an unbounded temporary file. Only the first 16,000 raw bytes are
  decoded/redacted, with a separate 16,000-byte UTF-8 display cap. Extra output is discarded
  and truncation is explicit. Invalid UTF-8 uses replacement characters.
- Credential-pattern redaction holds state across pipe chunks before any worker event.
  It covers supported labels/private-key formats, not arbitrary secrets. Output clipping
  occurs after redaction. The terminal view renders text, never HTML or terminal commands.
- Each command emits at most 64 numbered events, normally no faster than five updates per
  second, plus start/final metadata within that budget. If the event budget is exhausted,
  remaining captured output waits for the final event. Child applications may buffer their
  own output; Python commands use an unbuffered child environment.
- Sanitized deltas persist through the existing authenticated SQLite/event replay path.
  Reconnect/reload reconstructs them without repeating execution or duplicating text.
  Existing retention limits can omit older events; the panel marks a gap when observable.
  Conversation deletion removes its task/output rows through existing cascade cleanup.

Stop/timeout closes owned command resources. Windows Job Objects bound the command's owned
process tree, including children inheriting stdout. If the worker is forcefully terminated,
a final output frame may be absent: Studio displays an interrupted/unknown command outcome
with any already persisted partial text. Completed side effects are not undone. No unrelated
Python/Ollama process is terminated. This remains user-permission execution, not OS isolation.

Background `start_command` now shares bounded output and supports optional
[owned loopback readiness checks](background-commands.md), with a read-only status tool.
The panel retains the latest three commands plus up to four active owned servers.
Old release snapshots need rebuilding to include these features.

## Development and verification

The host-only `Coding.output` sink is not model-configurable. Manager validates profile,
identity, sequence, types, per-command bytes/frame count and terminal state before storing
events. Tool schemas and command allowlists are unchanged. Git's internal configuration/
path parsing explicitly retains bounded original text so redaction cannot hide policy keys
or weaken fingerprints; that host-only mode cannot attach a live-output sink.

Run `python -m unittest tests.test_command_streaming -v` from the project environment.
Set `LIVE_STUDIO_UI=1` for `tests.test_tool_profile_ui` to check actual live output,
reload/reselection, cancellation and independent verifier cards. These execute real local
processes; model metadata/inference replies elsewhere in the UI suite are explicit fixtures.

The pipe design follows [Python subprocess documentation](https://docs.python.org/3.12/library/subprocess.html);
owned nested-job behavior follows [Windows Job Objects documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
Neither API supplies an OS sandbox or portable cross-platform subtree guarantee by itself.
