# Task-scoped Studio activity

Open a conversation, then use **Activity task** to inspect one of its runs. The default
is its active task, or its most recent task when none is active. Starting a new run or
opening a Task history row selects that run. Switching conversations resets the choice.
Activity, command output and the last context estimate belong to the selected task;
events with an unknown or foreign task ID do not appear in that view.

Browser and Desktop workspaces show the latest received PNG only when its task matches
the selection. Selecting a task without an image shows the screenshot placeholder.
Previews are transient: reconnect/replay clears the image, and stored event history
contains no screenshot pixels. Only one latest preview is retained in UI memory; a later
preview can replace an older task's image. Selecting old history does not regenerate it.
Explicit user attachments remain separate and keep their existing persistence behavior.

Task state describes the selected run's current readiness. **Ready** means it is idle;
the task's outcome remains visible in its selector/history. A task in another conversation
does not make this view say **Working** or **Needs your approval**. **Open active
conversation** returns to that task. Global stop controls remain global, and pending
approvals remain visible regardless of selection. The approval dialog identifies its
source chat and task and offers **Open approval conversation**. Changing the view does
not grant, renew or replay an approval; backend identity, expiry and resource checks apply.

The presentation is split into `ChatMessages`, `ModelsPanel`, `WorkspacePanel`,
`TaskHistory`, `ActivityPanel` and `ActionApproval`. `App` retains connection, submission
and shared-state coordination. API events carry unknown raw payloads. Known approval,
command/readiness and activity payloads are validated into typed display contracts;
malformed plans/verifications remain inert JSON observations. Unknown extensions do not
gain command or approval authority. Existing redaction and replay limits are preserved.

Verification uses strict TypeScript/Vite builds, Node selectors/contracts/replay tests,
and rendered Edge against real Studio/worker/SQLite/tool execution. The scoped scenario
uses a controlled loopback page, a real Edge screenshot, separately approved file
creation and unittest execution, and conversation/task switching. Its model responses
are explicitly protocol fixtures; this does not certify local inference quality.
Native installation and the managed Ollama manifest-access failure remain separate gates.

Use `npm test` and `npm run build -- --configLoader runner` inside `desktop/`. From the
repository root set `LIVE_STUDIO_UI=1`, then run
`python -m unittest tests.test_tool_profile_ui -v`. To exercise a previously built sidecar,
set `FROZEN_BACKEND_TEST_EXE` to its absolute executable path. The scoped browser fixture
explicitly selects installed Microsoft Edge; it does not claim bundled Chromium discovery.
Paging, backups/restore and retention remain P1-06 B. This UI separation adds no execution
backend, native privileges or dependency.

At window widths of 1000px or less, use **Activity** in the header to open the selected
task's activity drawer. Escape or **Close activity** closes it and returns keyboard focus
to the opener. Wider windows keep the activity panel alongside chat/workspace views.
Changing width does not change the selected task or grant any permission.

Dialogs keep background controls inert and cycle Tab/Shift+Tab within visible enabled
controls. Escape closes help, rename/delete confirmation, screen-capture confirmation,
attachment preview and memory-forget confirmation without performing the action. It
**denies** a tool approval. Approval dialogs initially focus **Deny**, identify their task,
and provide **Emergency stop** directly; approving still requires an explicit button
action. The drawer also offers emergency stop while it covers the main header. A new
approval appears above an already open drawer and returns to it when resolved. Dismissal
returns to the original control when it still exists; navigation may remove that control.
These browser accessibility checks do not replace native WebView/installed-app acceptance.

The Windows ASGI listener uses its own Selector loop to avoid an unhandled Proactor
socket-shutdown reset observed during real client teardown. Global loop policy and fresh
worker defaults are preserved: Playwright/subprocesses retain Proactor support. No
exceptions are filtered and the no-unhandled-traceback tests remain strict. Windows
Selector is limited to 512 sockets; this is a local single-task server, with no broader
concurrency claim. See [Python's Windows loop constraints](https://docs.python.org/3.12/library/asyncio-platforms.html#windows)
and the [transport cleanup source](https://github.com/python/cpython/blob/v3.12.14/Lib/asyncio/proactor_events.py).
