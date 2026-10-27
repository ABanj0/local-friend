# Resumable read-only repository inspections

In **Workspace**, expand **Read-only inspection with checkpoints**. Enter one project-relative
file per line, or open a file and choose **Add open file to inspection**. Ask a question and
select **Start read-only inspection**. The local model plans, reads selected files and reports
its analysis through the normal task/activity interface. The backend checks that every
selected file has an actual successful read before accepting a complete report.

This is a dedicated subset: 1–8 existing UTF-8 files, at most 64,000 bytes each. The only
tool is `read_file`, limited to those exact paths. No writes, commands, Git operations,
browser/desktop actions, attachments, earlier chat or saved memories are available. Large
files/tool responses can still exceed the chosen inference context; use smaller inputs
or appropriate model settings. A checkpoint never silently truncates its stored transcript.

After a completed checkpoint, **Pause at next inspection boundary** requests a deferred
pause. A running model call/read finishes first. The UI shows a request in progress until
the next completed step is committed and acknowledged and the owned worker is stopped.
Use normal cancellation/emergency stop when waiting is unsuitable. Cancellation closes
the continuation; it does not promise to undo completed actions in other task modes.

Paused inspections survive closing/reopening Studio. Open the run in **Task history**,
then choose **Resume inspected files**. Unexpected backend/worker crashes can also leave
the last completed read-only checkpoint available. Resume is always explicit; startup
never replays a task. It creates a linked task, preserving previous journals/results and
continuing after the saved step without replanning or repeating acknowledged reads.

Resume rechecks current approved scope, project directory identity, every selected file's
identity/content/version, checkpoint/prompt/tool-schema version, saved history identity,
memory-forget epoch and local model digest/Ollama version. It uses the recorded inference
options and remaining step budget. Changed, replaced, deleted, linked, inaccessible or
unsupported inputs require reconciliation and a fresh inspection. Current UI tool access
cannot widen the continuation. Restoring a backup creates a new store identity, requiring
a new inspection rather than resuming a copied checkpoint.

Checkpoints are bounded JSON, never pickle or live handles. They store only a fixed trusted
prompt and validated completed read call/results; hidden reasoning and approvals are
excluded. The checkpoint transaction requires matching completed journal operations.
Only a committed checkpoint can be acknowledged. A lost acknowledgement/crash can leave
the last durable boundary available; uncommitted reads may be repeated after explicit
resume because this subset has no external mutations. Unsupported histories never resume.

Each checkpoint is limited to 1 MiB. There are at most three linked attempts, with the
original model step limit preserved. Per-task supervision deadlines apply to each attempt;
time spent paused is not a total execution-time guarantee. No automatic retry occurs after
admission, commit or startup failure. Ordinary agent/browser/desktop/coding tasks retain
their existing interrupted/unknown behavior and do not gain pause/resume support.

Checkpoint transcripts are private database content, included in unencrypted Studio backups
and removed with their source conversation. Retention previews include their row/byte cost;
cross-conversation checkpoint references fail closed. This is logical policy enforcement,
not OS isolation from another process running with the same Windows permissions.

Authenticated integrations use `POST /inspections` with conversation, objective, model,
project, selected files and inference options. `GET /tasks/{id}/inspection` returns bounded
status metadata, never the transcript. Empty-body `POST /tasks/{id}/inspection/pause` and
`.../resume` request controls; resume accepts no model, tool, settings or approval overrides.

Run `python -m unittest tests.test_inspection tests.test_inspection_http -v` for contract,
real worker, approval denial, pause/restart, crash and precondition tests. The rendered
checkpoint scenario uses actual APIs, SQLite and backend restart with explicit inference/
native-IPC fixtures. Actual-model quality and native installed-product acceptance are
separate gates; successful file reads do not certify the correctness of model analysis.

Protocol references: [Python SQLite transactions](https://docs.python.org/3/library/sqlite3.html#transaction-control)
and [Ollama tool messages](https://docs.ollama.com/capabilities/tool-calling).
