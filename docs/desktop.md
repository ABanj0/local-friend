# Local Agent Studio

Status: **native lifecycle and installed-product acceptance passed2026-10-28**, including
Standard-user VM install, actual version upgrade, retained history/settings/attachments and
both uninstall data modes. See `IMPLEMENTATION.md` and the [VM evidence guide](windows-test-vm.md).
The0.1.1 package is an isolated upgrade-test fixture, not a published production update.
The existing `launch.ps1` CLI remains available.

## Install prerequisites once

1. Install the current Node.js LTS from [nodejs.org](https://nodejs.org/en/download).
2. Follow [Tauri's Windows prerequisites](https://v2.tauri.app/start/prerequisites/):
   install Microsoft C++ Build Tools with **Desktop development with C++**, the Windows
   SDK, WebView2 Runtime, and Rust using the MSVC toolchain. Accept any installer elevation
   yourself; the agent does not require ongoing administrator privileges.
3. Ensure [uv](https://docs.astral.sh/uv/getting-started/installation/) is available.
   Reopen PowerShell and check `node --version`, `npm --version`, `cargo --version`,
   `rustc --version`, and `uv --version`.
4. In `C:\path\to\local-friend`, run ` .\scripts\setup-desktop.ps1`. This installs isolated
   Python dependencies, Chromium and frontend packages. It updates `uv.lock` and creates
   `desktop/package-lock.json`; review and retain these generated locks after success.
   Ollama itself is a separate runtime: use the [official Windows installation](https://docs.ollama.com/windows)
   or the existing portable runtime as configured below. setup-desktop.ps1 installs the
   Python/browser/frontend dependencies; it does not install Ollama.
5. Run ` .\desktop-dev.ps1`. One command starts Vite and Tauri; the application starts
   its Python service and starts or connects to Ollama. Use **Models & settings** to check
   availability. No separate backend/model terminal is needed during normal application use.

If PowerShell blocks scripts, follow your machine's approved script-signing/execution
policy. Do not disable security controls. The equivalent development commands are
`uv sync --python 3.12 --extra automation --extra desktop --extra dev --extra bundle`,
then `npm install` and `npm run desktop` from `desktop`.

## Workspaces and controls

Agent/Browser/Desktop/Workspace views include a per-task **Tool access** selector.
See [capability profiles](tool-profiles.md) for supported categories and CLI/API behavior.
Unified preserves the existing multi-category workflow. Regeneration retains the original
task profile; existing approval and scope rules apply to every choice.

- **Chat:** contextual streaming, Markdown/code blocks, copy, regeneration and cancellation.
  New completed replies show tokens/s, generated tokens and elapsed time. Speed comes from
  Ollama's generation timing, excluding loading and prompt processing; elapsed time includes
  the full worker request. Agent replies show totals across model calls, including planning.
  These statistics persist with history; old messages and cancelled runs have no statistics.
  Regeneration appends a new answer to the latest user request. Create another conversation
  when the context budget is exceeded. Model/temperature/context choices persist in SQLite.
- **Agent:** one objective may use browser, desktop and coding tools. Plans, actions and
  results are separate events. Cancellation kills the owned worker tree; completed edits
  are not rolled back. Pause/resume is deliberately unavailable.
- **Browser:** isolated visible Chromium, URL/action history, requested screenshot previews,
  and download paths/byte counts in tool results. Ask for `browser_intervene` when login is
  needed; enter credentials in the browser and approve continuation. Domain scopes remain
  enforced, including authentication providers and resources. Nested submission approvals
  appear before the continuation approval. WebSockets are blocked by the existing browser
  policy, so some sites are incompatible.
- **Desktop:** Notepad launch shortcut, accessibility tools, requested screenshots, action
  history and emergency stop. Interactive Windows automation requires an unlocked desktop.
- **Workspace:** select a directory inside `agent.toml`'s workspace, inspect files and request
  edits/tests. New-file contents and overwrite diffs require review in Studio. Test output
  and Git diffs appear in tool results; commands remain restricted to configured profiles.
- **Models:** installed models, loaded state, available CPU/GPU/memory statistics, inference
  parameters and read-only permission scopes. Model installation remains an explicit setup
  action: use the existing `scripts/pull-model.ps1` or Ollama's documented pull command.

Scope changes require editing `agent.toml` and restarting the backend. A folder picker
does not grant access outside the configured workspace. The permission panel cannot silently
expand scopes. Existing configuration files are not overwritten by setup.

## Production build

Run ` .\scripts\build-desktop.ps1` after setup and validation. It runs regression tests and
lint, builds a PyInstaller sidecar, then runs Tauri's Windows NSIS build. Output belongs in
`desktop/src-tauri/target/release/bundle/nsis/`. The updated Ollama-discovery build produced
`Local Agent Studio_0.1.0_x64-setup.exe` (74,098,719 bytes), independently verified against
`dist/release-manifest.json` with successful bundling. Its SHA-256 is
`904b5a0010f258ce4acc2a57851e32c2f37df22777f066dbeef768de523103f7`.
Seven new frozen startup/runtime/coding/MCP checks pass, with no skips. The original owner
build's17 frozen and7 Rust passes remain historical evidence. Managed model-store access
remains denied for separately launched managed servers. Subsequent installed recovery
verifies automatic normal-session startup, a completed330-token chat, and real browser/
memory workflows against the installed executable. Later native lifecycle/control and
guest upgrade/uninstall acceptance pass; managed owned-server limits are historical and
specific to their execution context. See the dated evidence in IMPLEMENTATION.md.
The historical managed10013 download failure does not block this produced artifact. Use
` .\scripts\build-desktop.ps1 -ConfigLoaderRunner` if the normal Vite config loader hits
the documented parent-directory access restriction. This uses a temporary build overlay.
`dist/release-manifest.json` records artifact SHA-256, source/lock hashes and Python build
environment versions, including partial output after a bundling failure. It does not
certify installation or provide a complete binary SBOM.
For an installed main EXE, compare `expected_nsis_main_payload.sha256` only when its status
is `predicted`. Tauri patches a bundle tag for NSIS and restores its build-folder copy,
so that raw build EXE hash can differ. The expectation applies to unsigned default patching;
signed/unknown or ambiguous inputs are explicitly unavailable. It is not an extracted-payload
or signature certificate. The current prediction matches the installed EXE. This behavior
is documented in [the pinned Tauri bundler source](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.12.4/crates/tauri-bundler/src/bundle.rs).
Packaging follows the official [Tauri Windows installer](https://v2.tauri.app/distribute/windows-installer/)
and [sidecar](https://v2.tauri.app/develop/sidecar/) mechanisms.

The earlier2026-10-26 release candidate includes the qualified file-memory UI and backend:
`.runtime/roadmap-gates/after-memory-20261026/Local-Agent-Studio-0.1.0-release-candidate.zip`.
Its `release-validation.json` and `release-manifest.json` record the build, exact archive/
member hashes and six passing deployed-sidecar checks. Extract the entire archive into a
new directory, keeping both EXEs and `resources/agent.toml` together. Close other Studio
instances before normal-session native testing. This archive is a release candidate,
not an installer, and its native-window/recovery/install/upgrade acceptance is pending.
Building generated artifacts while `tauri dev` is watching may restart the development
instance; complete active work before running a release build.

The candidate uses the installed CLI's supported `--no-bundle --ci` mode with a temporary
`beforeBuildCommand` runner overlay and offline Cargo; permanent configuration is unchanged.
Its managed-session NSIS acquisition retry failed10013; the later owner build succeeded.
The exact pinned dependency URL/hash comes
from [Tauri CLI2.12.4's bundler source](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.12.4/crates/tauri-bundler/src/bundle/windows/nsis/mod.rs).
For the actual installer, use the full build script from an ordinarily permitted network,
then follow standard-user installation and upgrade acceptance. A successful candidate build
does not satisfy those gates.

The production app uses `%LOCALAPPDATA%\local.agent.studio\agent.toml`, copied from a
credential-free template on first launch only. Defaults are published completely and
exclusively on NTFS; concurrent launches preserve the first configuration. Its workspace/state are relative to that
directory. Configure the workspace explicitly to reuse your development workspace.
Models, Python development environments and browser binaries are not inside the installer.
Install Ollama normally and pull your selected model. The package template uses installed
Edge (`[browser] channel = "msedge"`). To use Playwright Chromium instead, remove that
channel and install the matching browser build in the configured user environment.
Coding profiles need a separate Python interpreter:
set `[runtime] python = 'C:\path\to\local-friend\.venv\Scripts\python.exe'` in production
configuration. Without it the app uses `python` on PATH. A frozen backend is not a general
Python interpreter. Real frozen-worker browser/screenshot and approved external-Python
checks pass; actual Standard-user guest installation and native WebView acceptance now pass.
This does not bundle a development Python runtime or establish arbitrary coding-task quality.

### Reuse this repository's portable Ollama in the installed app

The installed app's configuration directory differs from the development checkout. If
`Ollama is missing` appears and the runtime lives in `C:\path\to\local-friend\.runtime\ollama`,
install the updated Studio package, close Studio, then run from a normal PowerShell:

```powershell
cd C:\path\to\local-friend
.\scripts\configure-installed-ollama.ps1
```

The helper adds trusted runtime paths to the existing installed configuration, makes an
exact backup beside it and preserves other settings. A differing existing `[ollama]`
section is refused for manual review. It changes no global PATH, moves no model files and
downloads no models. Open Studio from Start afterward; it starts/connects to Ollama.
The script requires the updated backend with these settings; rebuilding alone does not
replace an already installed application.

Equivalent manual entries in `%LOCALAPPDATA%\local.agent.studio\agent.toml`:

```toml
[ollama]
executable = 'C:\path\to\local-friend\.runtime\ollama\ollama.exe'
models = 'C:\path\to\local-friend\.runtime\models'
```

Startup checks an existing service first. For a new owned service, explicit executable
configuration takes priority, followed by the configuration-local portable runtime, PATH,
the standard per-user Windows install and Program Files. Relative explicit paths resolve
against agent.toml's directory. `[ollama].models` selects an existing model store; otherwise
the development portable runtime keeps its existing store and standard installs retain
their inherited/default model directory. Running unrelated services retain their own
configuration and are never stopped or repointed. Invalid explicit paths fail clearly.
Owned startup validates the loopback endpoint and removes the Studio credential from the
child environment. See [Ollama's Windows documentation](https://docs.ollama.com/windows)
for the standard binary location and `OLLAMA_MODELS` behavior.

The owner applied this correction successfully: installed code/config match the update,
original settings are preserved, Studio owns its Ollama process and both downloaded models
are visible. A completed chat and separate real browser/memory workflows verify inference
through that normal-session service. Managed private-server model access denial does not
imply the installed app cannot infer. See .runtime/p0-05-installed-ollama-recovery/validation.json.
The owner also verified that native replies, Copy and Stop work. The remaining native
approval/recovery/single-instance/upgrade checklist below still applies.

To repeat frozen acceptance after building the sidecar:

```powershell
$env:FROZEN_BACKEND_TEST_EXE = (Resolve-Path 'dist/agent-backend.exe').Path
$env:FROZEN_LIVE_MODEL = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_studio_runtime tests.test_studio_socket tests.test_frozen -v
Remove-Item Env:FROZEN_BACKEND_TEST_EXE,Env:FROZEN_LIVE_MODEL -ErrorAction SilentlyContinue
```

The live browser check requires the configured local Ollama model and installed Edge.
The external Python check uses the test interpreter in a disposable project, with a real
approval round trip. No installed-release or physical desktop pass is inferred.

If NSIS download fails, rerun the build from a normal Windows terminal with permitted
access to the official Tauri GitHub release downloads. The observed failing dependency
is `https://github.com/tauri-apps/binary-releases/releases/download/nsis-3.13/nsis-3.13.zip`.
Keep existing firewall/security policy; resolve access through your normal allowed network.
After a successful build, verify the installer hash against `dist/release-manifest.json`,
then perform the separate standard-user installation and upgrade checklist.

For the produced installer, close development Studio first, run the setup EXE normally,
then launch the installed application and complete the native checklist below. The generated
installer script uses currentUser mode. Keep the existing production configuration/history;
configure an approved disposable workspace for tool tests. Actual guest testing verifies
default uninstall retains history/configuration; reinstall reopens the same records.
Selecting **Delete the application data** removes both `%LOCALAPPDATA%\local.agent.studio`
and `%APPDATA%\local.agent.studio`, including the default workspace inside app data.
Move any wanted workspace files elsewhere before choosing that option. Unrelated outside
projects and the independent Ollama installation/model service survive the tested uninstall.

For repeatable clean-install/upgrade validation, use the separate
[Windows test VM guide](windows-test-vm.md). An isolated packaging-only0.1.1 installer and
the unchanged0.1.0 baseline are prepared under
`.runtime/p0-05-install-upgrade-fixture/artifacts/`; neither is installed on the host.
Their actual guest upgrade/retention/uninstall matrix passes2026-10-28. The0.1.1 fixture
changes packaging metadata only; it is not a new production release.

## Validation

Studio now stores [configured unittest observations](test-verification.md) independently
of model reports. `/test` fails verification for zero tests; skips/custom runners remain
explicitly inconclusive. Test execution still requires approval.
Reviewed coding writes also produce [artifact readback evidence](artifact-verification.md).
Matching file bytes and passing tests are separate observations, not whole-task certification.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m ruff check local_agent tests scripts/create-icon.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
$env:LIVE_STUDIO = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_studio.StudioLiveTests -v
Remove-Item Env:LIVE_STUDIO
```

API tests skip when FastAPI/httpx are missing; skips are **not passes**. Worker protocol
tests use a local test fixture with real subprocesses and tools; live tests use actual Ollama.
Run `npm run build` inside `desktop` to check TypeScript and production assets.
Run `npm test` there for the event-state tests (Node 24 LTS, no extra test dependency).
With built assets, `LIVE_STUDIO_UI=1` also enables `tests.test_studio_replay_ui`: it verifies
5,001 real SQLite events exactly once in rendered UI state through socket reconnect and
backend restart. Its native connection handshake is bridged; it does not test native IPC.

Desktop acceptance repeat procedure (recorded scopes/results are in IMPLEMENTATION.md):

1. Start the app, send two contextual chat messages, observe incremental tokens, copy an
   answer, regenerate it, cancel a long answer, and reopen the app to check history/settings.
2. In Workspace select `workspace/first-task`; inspect its files, request a deliberate small
   edit, review the diff, deny once, then approve a fresh request and run unittest.
3. In Browser navigate a permitted test page, fill a harmless field without submission,
   request a screenshot, and inspect action/download results. Test a denied submission.
4. In Desktop launch Notepad, type sample text, save to the approved workspace, and verify
   contents with file readback. Test emergency stop while a task awaits approval.
5. Submit a combined file-and-browser task. Verify both tool results independently.
6. Close/reopen during a task: unfinished work must be marked interrupted, never replayed.
   Restart the backend via the disconnect banner. Launch a second application instance:
   it should focus the existing window, not spawn another backend.
7. Build/install the NSIS package and repeat the above from the installed application.

## Troubleshooting and current blockers

**Task stays on “Working” with only a “started” event:** a Windows shutdown-pipe read
previously blocked spawned workers. This is fixed in the backend runtime. Fully close and
relaunch Studio with ` .\desktop-dev.ps1` to load the fix. New requests should show
`worker_ready`, planning progress, then a plan and tool/approval events. Frontend hot reload
alone does not restart the Python backend.

1. **Missing Node/Rust/MSVC:** complete the prerequisite steps above, reopen PowerShell,
   run setup, then rerun the build. No compilation claim is valid before this succeeds.
2. **Package download error 10013:** run setup in your ordinary approved user session with
   access to PyPI/npm/crates.io. If still blocked, ask the machine/network administrator
   to permit those development package sources. Do not disable firewall/endpoint protection.
3. **Ollama HTTP 500 / Access is denied:** this was reproduced only in the managed session
   used for implementation. Stop that owned test service, then start Ollama under your normal
   Windows account using the existing start-model script. Run
   `Invoke-RestMethod http://127.0.0.1:11434/api/tags`; the selected model must appear.
   Retry live tests. If access still fails, inspect the server log and model-directory
   permissions with your administrator; do not delete models or reset permissions blindly.
4. **Port 17861 occupied:** close the existing Studio window or its known owned backend.
   Never kill all Python processes. The backend intentionally refuses to share that port
   with another instance. A stale CLI `STOP` file also blocks tools; follow the existing
   emergency-stop recovery guide before removing it.
5. **Missing browser/desktop dependencies:** rerun setup, inspect `/health` dependency status
   through the app, and rerun the existing live browser/desktop tests in an interactive session.
6. **Backend crash:** use **Restart backend**. Conversations survive; tasks do not resume.
   Startup failures are returned to the UI. No command is automatically retried after a crash.

## Task deadlines and storage recovery

Studio supervises readiness, independent heartbeats and model/tool phases. It stops owned
workers on a deadline; token traffic cannot extend a phase indefinitely. Approval waits
persist as `waiting`, suspend active phase/task budgets and remain cancellable. Expiry
blocks the task. There is no checkpoint pause/resume.

Optional overrides in the central `agent.toml` use positive finite seconds:

```toml
[execution]
ready_timeout = 15
heartbeat_timeout = 10
model_timeout = 135 # Default: model.timeout + 15, rather than a fixed 135
tool_timeout = 120
execution_timeout = 30
task_timeout = 3600
approval_timeout = 300 # Must not exceed 300
```

Restart the backend after changing settings or updating its worker protocol. Heartbeats
are internal, transient signals; they are not model progress or durable activity events.

When completion storage is unavailable, the worker stops before persistence retry. The UI
shows **Waiting for storage**, authenticated `/health` reports degraded readiness and new
tasks stay blocked. SQLite busy waits are bounded at 0.2s and failed API writes return 503.
Retry commits only the selected outcome; it never reruns an action. Resolve disk space or
the specific database-access issue without deleting conversations or weakening permissions.
If the backend closes before a commit, the next working startup marks that task interrupted.
Permanent storage/OS cleanup failures cannot be certified as successful completion.

## Activity recovery and delivery limits

Restart the full app after this protocol update so the frontend and Python backend match.
The event socket authenticates first, captures a SQLite high-water cursor and delivers
history in acknowledged pages of at most 200 events, targeting 256 KiB. New events follow
after that captured boundary. Database identity and backend epoch prevent stale cursor
reuse; deleting a chat does not rewind allocated event IDs. Reconnecting replays events,
never tools or commands. SQLite still holds the durable history.

Only one delivery is in flight per socket. Send timeout is 5s, acknowledgment timeout 10s;
the UI reconnects after 2s using its last accepted durable cursor. The shared RAM ring holds
at most 4,000 events / 16 MiB. If it overflows, an explicit `ram_gap` snapshot replaces
streams and pending approvals, clears stale previews and catches up durable events.
Tokens stay in RAM; completed response text remains in messages. Old approval/preview
rows contain placeholders and cannot resurrect an actionable approval or screenshot.

The UI retains at most 10,000 activity entries / 16 MiB and displays the latest 40. Trimming
display history does not rewind its accepted cursor. Full activity browsing/retention
configuration remains a later increment. An individual frame above 16 MiB is rejected
explicitly (close 1009), rather than silently skipped. Inspect the persisted task via
Task history. Export needed messages, then explicitly delete the affected conversation
if oversized activity prevents synchronization; deletion requires confirmation and removes
that conversation. Reduce output before repeating the task. This is a delivery limit,
not an artifact-size or checkpoint-resume guarantee. Supported textual credential patterns are tested across streaming boundaries; arbitrary
formats, raw attachments and screenshot pixels remain outside best-effort detection.

## Security and extension

The backend binds only to `127.0.0.1:17861`. Each app launch gets a fresh secret over native
IPC; HTTP requires bearer authentication and WebSockets require a first-message credential
and allowed origin. There is no arbitrary shell endpoint. Task processes inherit existing
policy, audit logging and approval controls; trusted command execution is not an OS sandbox.
Screenshots and approval details are transient events, but screenshots also remain in the
existing tool state directory. SQLite contains conversation text and redacted output;
redaction is best-effort, not encryption. Keep credentials out of chat and project files.

Add tools in `local_agent/tools.py` with strict schemas and policy checks. Studio emits their
actual results automatically. Add tests for approvals, cancellation and failure paths. To
change models, install one in Ollama and select it in the UI; validate its native tool and
vision behavior before relying on agent automation.

## Reviewed resource versions

A file/Git resource changed while approval was pending is refused with a review conflict.
Inspect the concurrent content, then submit the operation again for a fresh review. No stale
approval is automatically reused. File identity and SHA-256 preimages accompany review;
Git commit also checks index identity and HEAD tree. Studio new-file review follows the
same path; CLI new files remain exclusive creates. File edits are limited to 64 KB and
Git review resource hashing to 16 MiB; an incomplete staged diff is refused.

Both P0-03 increments are implemented and tested. Writes use owned same-directory staging
and checked atomic replacement; new files/downloads publish exclusively and cannot replace
a late winner. Windows overwrites retain DACL entries/protection and require permission to
preserve them. Link/junction/reparse write and Git-metadata paths are refused. Hardlink
publication requires filesystem support; failures do not fall back to an overwrite.

Git refuses executable filter/signing/textconv/helper config and includes; supported
commits are unsigned, with hooks/fsmonitor/automatic maintenance/signature display disabled.
Use a separate manual reviewed workflow for repositories requiring includes, LFS filters or
signing; Studio never silently changes their config. External worktrees are refused.

Trusted host execution and remaining same-user path/Git races still apply. An OS failure
after publication may have completed an action; no rollback is guaranteed. A hard process
crash can leave an owned `.local-agent-*.tmp` in the approved destination directory; inspect
its exact location before manual cleanup. Do not delete unrelated files by a broad glob.

## Streaming privacy treatment

Generated output uses one bounded parser across chunks. Supported textual labels include
password/passwd, api_key/api-key/apikey, token/secret assignments, JSON quoted fields,
Bearer values and private-key blocks. Values are masked before live events; the completed
message uses the same treatment. Ordinary text streams with up to 16 characters of
lookbehind; private-header state is capped at 128 retained characters. Unterminated values
and abnormal private headers may over-redact rather than reveal a partial value.

This is best-effort text treatment. It does not identify arbitrary unlabeled/encoded
credentials or secrets in pixels, encrypt SQLite, or rewrite original attached files.
Token statistics still measure Ollama's original generation. Restart the backend after
updating; frontend reload alone does not replace the worker implementation.


## Image context and transient capture cleanup

Agent runs retain original user images across browser/desktop screenshots. The model
receives at most eight images total and only the latest transient observation. Each
observation is normalized to JPEG, at most 1600 pixels per side and 2 MiB. If eight
originals already fill the budget, the screenshot is explicitly omitted from model
context; its UI preview remains available. Invalid/oversize observations are reported.

Raw captures use `state/captures/<run>/` with a SQLite ownership registry and a
process-lifetime lease. Reads and deletion require a matching recorded file identity;
links and reparse points are refused. Successful consumption, normal shutdown and
Studio cancellation remove owned captures. Startup recovery acquires abandoned leases
before cleanup. Active runs, chat attachments, legacy screenshots and unknown files
are never swept by filename pattern. An unexpected/replaced file blocks cleanup and
is reported; inspect that exact run before manually resolving it. Do not clear the
registry or recursively delete arbitrary state directories to bypass the check.

Screenshots can contain secrets: pixel redaction and OS isolation are not guaranteed.
The local ownership registry is not protection against a hostile same-user process.
Physical Windows capture acceptance remains separate from browser/adapter tests.

To repeat the actual model/browser attachment checks in PowerShell:

```powershell
$env:LIVE_IMAGE_CONTEXT = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_vision.LiveImageContextTests -v
Remove-Item Env:LIVE_IMAGE_CONTEXT -ErrorAction SilentlyContinue
```

These checks require the configured local Ollama model and installed Edge browser.

## Startup diagnostics and recovery

After disconnect Studio attempts backend connection/recovery after 1, 2 and 4 seconds.
The budget is per mounted application session; **Restart backend** replenishes it.
Recovery never resubmits a task. SQLite reconciles interrupted task history on startup.
A live owned backend is reused, not terminated because of a socket disconnect. Health
probes time out after two seconds, with at most ten probes per connection attempt.

Backend diagnostics appear below the disconnected banner; model diagnostics appear in
Models & settings. These are bounded RAM tails, not persistent logs. Native output keeps
at most 16 KiB and omits sensitive/oversized lines; owned Ollama output keeps at most
8,192 characters through streaming redaction. Arbitrary secret detection is not guaranteed.
Output from an externally started Ollama service is not captured.

### Native validation results and repeat procedure

Installed focus, approval/no-replay, idle crash recovery and normal-close/reopen subchecks
now have owner observations plus independent process/store evidence in IMPLEMENTATION.md.
The installed [retry/fallback check](native-recovery-check.md) also passed in the owner's
normal session:1.09/2.02/4.05-second backoff lower bounds, exhausted automatic budget, manual
connection, normal-close cleanup and independent Python preservation. P0-05 first is complete;
do not repeat these steps unnecessarily. The native Windows file picker and text attachment
also pass with owner confirmation and independently verified fixture/message/model evidence.
Native Markdown export/download also passes with exact saved-file readback. Native
capture/preview also passes with owner confirmation and independently verified persisted
JPEG metadata. The separate Standard-user Windows guest matrix now also passes actual
installation/upgrade/history/uninstall, native controls and new real model replies. See
IMPLEMENTATION.md and [the guest matrix](windows-test-vm.md); P0-05 third is complete.

The [independent-Ollama native check](native-shared-model-check.md) now also passes in the
owner's installed session: the model survives Studio normal close, then the harness cleans
only its own fixture. The guest matrix independently preserves its actual Ollama identity
through upgrade and both uninstall modes. Completed checks need no repeat unless relevant
changes or a regression justify it. OS-isolated agent execution remains a separate gap.

Use the [bounded native startup diagnostic](native-diagnostics.md) to collect safe
failure categories before repeating these acceptance steps. It never certifies the UI.

The managed-session check failed with WebView2 0x800700AA while another Studio was running.
Its existing instance was preserved. Component/browser passes do not close this gate.

1. Finish or cancel a disposable task and close Studio normally. Leave unrelated Python
   and Ollama processes alone. Build and launch from your normal Windows session.
2. Set `$env:TAURI_CONFIG = Get-Content desktop/src-tauri/tauri.dev.conf.json -Raw`, then run
   `cargo test --offline --manifest-path desktop/src-tauri/Cargo.toml` and
   `cargo build --offline --manifest-path desktop/src-tauri/Cargo.toml`.
3. Launch with `desktop-dev.ps1`. Open a second instance and verify one window and one owned
   backend remain. A continuing resource conflict needs investigation; do not clear your
   profile or weaken browser security to bypass it.
4. Verify chat and an approved file/test workflow in a disposable conversation. To test a
   crash, identify the Python runtime child of this exact Studio PID before stopping that
   child only. Verify bounded recovery, interrupted status and no repeated action.
5. Close Studio normally. Confirm its backend/workers exit and independently launched
   Python/Ollama processes remain alive. Record native results separately from browser
   tests. Installer/upgrade acceptance is now recorded separately in the completed VM matrix.
