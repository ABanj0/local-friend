# Local Windows Agent

Type `/` in the Studio composer for commands such as `/plan`, `/goal`, `/test`, `/diff`
and `/summarize`. See [slash command usage and goal behavior](docs/slash-commands.md).

Studio supports chat rename/delete/search/export, file and image attachments, screenshot
paste and confirmed screen capture. See [chat features and limits](docs/chat-features.md).
Agent tasks support Unified, Coding-only, Browser-only and Desktop-only tool access.
See [profiles, CLI examples and tool contracts](docs/tool-profiles.md).
Configured unittest runs now have [persisted test observations](docs/test-verification.md),
separate from model prose. Zero discovered tests are not verified; skips remain explicit.
Coding writes also produce [artifact readback/hash evidence](docs/artifact-verification.md).
Workspace and coding agents support [bounded repository text search](docs/repository-search.md)
with clickable file results and explicit coverage limits.
Coding agents can propose [related-file patch sets](docs/patch-sets.md) with one diff review,
expected preimage hashes and separate readback evidence for each file.
Approved foreground commands show [live, bounded command output](docs/command-streaming.md)
in the activity panel, with redacted partial output retained across reconnect and cancellation.
Background commands now have [bounded logs and optional owned-service readiness](docs/background-commands.md),
including a read-only status tool and cleanup when the task ends.
The [versioned agent evaluation corpus](docs/agent-evaluations.md) defines twenty model tasks,
eight separate safety cases and strict result scoring. Its runner executes production
Agent/Tools in disposable scopes; corpus validation alone does not execute tasks. Actual
model-quality acceptance remains separate from protocol-fixture integration results.
The [measured Qwen baseline](docs/agent-evaluation-baseline.md) passed 55/60 samples
(91.7%) and all eight safety cases; five workflow failures remain recorded.

Task history offers [content-free run diagnostics](docs/observability.md): correlated spans,
approval/tool/model timing, verifier links and JSON export without chat/tool contents.
It also offers an [execution journal and recovery inspection](docs/execution-journal.md):
committed tool intents/results, interrupted or unknown effects, file precondition comparisons
and a fresh-instruction action. It never replays actions or claims checkpoint resume.
Model settings now share [validated inference options and capability checks](docs/inference-options.md)
across chat, plans and agent calls, with configurable output/thinking/residency, incomplete
response handling, and prompt/load/first-token timing details.
The composer shows a conversation-scoped [context estimate](docs/context-budget.md).
Bounded compaction preserves instructions, images and verifier references; oversized
protected context stops with a clear notice. Stored conversations remain intact.

Studio also has [explicit project memory](docs/project-memory.md): save notes or selected
messages, search across conversations, inspect source references and confirm forgetting.
Retrieved historical notes confer no permissions; memory remains local and project-scoped.

The [task-scoped activity panel](docs/studio-activity.md) lets you select a run within a
conversation. Its activity, command output, context estimate and screenshot stay with
that task; global approvals identify their source conversation.

Measured model results and tuning decisions are in
[the local performance report](docs/model-performance.md). Repeat the checks with
` .\.venv\Scripts\python.exe -m local_agent.benchmark` while Studio has no active task.

## Desktop application work

Local Agent Studio uses Tauri 2 / React / TypeScript / Tailwind, a FastAPI/WebSocket backend,
SQLite persistence, and the existing local agent tools. A compiled Windows debug executable
exists. Browser-based UI acceptance and development build checks pass; **native Windows
end-to-end acceptance and a verified installer remain incomplete**.

Start with [desktop setup, launch, build and troubleshooting](docs/desktop.md).
P0-05 lifecycle changes add bounded in-memory diagnostics and three automatic recovery
attempts with manual fallback. Interrupted tasks are never replayed. Component and
browser checks pass; native acceptance remains open after a managed-session WebView2
resource conflict. See [current evidence](IMPLEMENTATION.md).
After installing prerequisites, run ` .\scripts\setup-desktop.ps1`, then
` .\desktop-dev.ps1`. The intended production build command is
` .\scripts\build-desktop.ps1`; no Windows installer exists yet.
The PyInstaller sidecar and optimized release EXE now build and pass 15 frozen runtime,
security, approved-coding and real-model browser checks. NSIS download remains blocked
by managed-session socket error 10013. Artifact hashes and build inputs are recorded in
`dist/release-manifest.json`; installation remains unverified.

The current acceptance baseline is dated **2026-10-22**. Required Python/API packages,
Node, Rust and lockfiles are present. Earlier missing-tool and primary-model-access reports
in the implementation history are superseded by the verification below.

## Existing command-line agent

A local-only Ollama controller with Playwright browser tools, Windows accessibility tools,
scoped file editing, Git and development command profiles. One natural-language task can
use all tool categories. The 2026-10-22 baseline passed local inference, GPU allocation,
tool calling, vision and a real browser-to-file model workflow. Public browser and Notepad typing/save/readback
acceptance now pass in the user's normal Windows session. A real local-model counter bug-fix
workflow also passes, completing P0-01's acceptance baseline. **Full platform acceptance remains
incomplete:** wider desktop, native application and installed-release checks remain open.
Managed-session access restrictions remain separate.
An earlier managed Ollama launch could not open the Qwen manifest (Access is denied).
Current inference/GPU/vision/tool/browser checks and counted counter acceptance pass
against the existing configured service. This does not establish that the separate
portable-server manifest permission issue was repaired. See the dated evidence below.
See [IMPLEMENTATION.md](IMPLEMENTATION.md).

For exact commands, expected results and remedies for each open requirement, follow
[the step-by-step recovery guide](docs/recovery.md).

## Current verification

| Capability / check | Evidence and remaining limits |
| --- | --- |
| Current model availability, 2026-10-23 | Existing configured service supports actual GPU/structured/tool/vision/browser checks, the 55/60 corpus baseline and counted counter acceptance. The earlier portable managed launch's manifest-access failure has not been retested. |
| Default regression, refreshed for P1-08 A observability | 363 unique tests: **328 passed, 35 skipped**, 142.349s. All 70 targeted checks, nine rendered scenarios and thirteen rebuilt frozen-backend/UI/runtime checks pass. TS/Vite, eleven Node tests and Ruff pass. Model-dependent regression remains blocked; skips remain unpassed. |
| Latest default regression, P1-08 B corpus contract | 383 unique tests: **347 passed, 36 skipped**, 144.823s. All twenty new component tests pass with the local-browser denial enabled; Ruff and packaged-wheel corpus checks pass. This verifies definitions/oracles/scoring, not actual model-task execution or quality. |
| Latest runner regression and live baseline | **366 passed / 37 skipped**, 403 unique defaults, 150.708s; 41 targeted passed / 2 skipped; protocol matrix 60/60 plus 8/8 safety. Actual corpus 55/60 (91.7%), 8/8 safety, five retained failures. Five separate real-model checks pass. Ruff/wheel/load checks pass; see the baseline's scope and counter-verdict limitation. |
| Latest counted coding acceptance | **370 passed / 37 skipped**, 407 unique defaults, 149.320s; 28 targeted passed / 1 skipped; actual counted counter opt-in passed (23.628s). Initial 3 tests/1 failure, repaired 8 passed, independent counted 8 passed, separate 6-test oracle and diff review. The earlier counter-verdict gap is resolved; P1-02 A/B are complete at their contracts. |
| Task lifecycle | Atomic completion, owned-worker cleanup, storage retry without action replay, heartbeat/phase/task budgets and approval waits verified. Captured-boundary replay, bounded acknowledged delivery and RAM-gap recovery are verified. |
| Real-model coding acceptance | **1 passed, no skips**, 20.049s. Qwen fixed the seeded counter, generated five tests, passed eight project tests and reviewed its diff; independent rerun and six behavior checks passed. |
| Normal-session browser validation, user-reported | **111 tests: 99 passed, 12 skipped**, 36.246s, after the public-test repair. All four browser tests enabled; skipped model/desktop/UI checks are not passes. |
| Normal-session Notepad validation, user-reported | **111 tests: 96 passed, 15 skipped**, 48.994s. Physical launch/type/save/file readback passes; wider desktop and native Studio behavior remain unverified. |
| WebSocket security acceptance | **9 passed, no skips** against real isolated backends: invalid/missing authentication, timeout, malformed frames/cursors, forbidden origins and valid snapshots. |
| Startup compensation, refreshed for P0-02 | **10 passed, no skips**: real gated workers, startup fault/cleanup checks, redacted API failure and explicit retry. |
| Durable replay, sockets and rendered UI | **15 passed, no skips**, 25.531s; all 5,001 events once through reconnect/backend restart, slow clients, transient privacy and cursor gaps. Six separate Node state tests also pass. |
| Real Studio/Ollama and browser UI, refreshed for P0-02 | **5 passed, no skips**, 31.729s: contextual stream/read-tool/cancel and both UI scenarios, including approval and real SQLite-lock recovery. Native connection IPC alone is bridged. |
| Python lint | Ruff passed. Dependencies and lockfiles are unchanged. |
| Local inference / GPU / tools / vision / local browser | Prior 2026-10-22 architecture audit: **11 of 12 live tests passed**; combined model-driven browser/file workflow passed. These model measurements are historical; current socket tests require no inference. |
| Public browser | **Passed in the user's normal Windows session**, using Playwright's testing demo: extraction, app-route navigation, two tabs and draft input with no submission. Managed-session restrictions remain separate. |
| Frontend / Rust / Windows delivery | Current TypeScript and Vite production builds pass. Prior Rust development check passed; debug EXE exists. Notepad acceptance passes; wider desktop/native lifecycle and installed release remain unverified. |

Skips are not passes. See [current results and historical evidence](IMPLEMENTATION.md),
the [roadmap](ROADMAP.md), and the versioned [lockfile/source baseline manifest](docs/acceptance-baseline.json).
The manifest records exact locked dependency versions and source hashes at P0-01; it remains
a point-in-time snapshot. Later changes are recorded in IMPLEMENTATION.md. Its local source
snapshot supports review without creating a Git commit. P0-01 through P0-04 and P1-01's
registry/profile contract are verified at their documented scopes. P0-05 native/install
gates remain open. Current model access is available through the existing service.
P1-02 A/B's verifier, search, patch and command workflows satisfy their documented
engineering and counted real-model acceptance contracts. P1-08 A's Studio diagnostics
and B's corpus/runner gate are verified; the five baseline workflow failures remain.
Next: P1-04 numbered migrations and durable operation records. This is ongoing roadmap
work, not full platform acceptance.

## Installation

Requirements: Windows 10/11, Git, uv, current NVIDIA driver, network access for installation,
and approximately 15–20 GB free for Python, browser, runtime and a model. In PowerShell:

```powershell
.\scripts\setup.ps1
.\scripts\start-model.ps1
```

The model server occupies that terminal. In another terminal:

```powershell
.\scripts\pull-model.ps1
.\.venv\Scripts\python.exe -m local_agent doctor
.\scripts\validate.ps1 -Browser -Model
.\launch.ps1 "Create hello.py in the workspace, write tests for it, run them, and report results."
```

Setup uses an isolated Python 3.12 environment and workspace-local caches. It resolves
dependency ranges in `pyproject.toml`, creates `uv.lock`, records `requirements-installed.txt`,
installs Chromium, and verifies the official portable Ollama archive against its release
SHA256 digest. `uv.lock`, `desktop/package-lock.json` and `desktop/src-tauri/Cargo.lock`
already exist. Keep their reviewed versions; restore Python packages with `uv sync --locked`
and the needed extras, and frontend packages with `npm ci`. Setup does not change execution
policy, firewall rules or system PATH.
Ollama itself may create its normal per-user identity/configuration under your profile.

If PowerShell blocks scripts, follow your organization's signing policy. Do not disable
security controls. No administrator rights or paid inference keys are required.

## Configuration and usage

`agent.toml` is the trusted central configuration. Paths are relative to that file.
Put projects to be edited beneath `workspace/`; do not point it at your entire user profile.
Only exact configured browser origins are allowed, including redirect and subresource
origins. Add a local development origin such as `http://127.0.0.1:8765` manually before use.
Set `browser.channel = "msedge"` to use installed Edge instead of downloaded Chromium.

The default commands are `test` (unittest), `lint` (Ruff), `build` (compile Python), and
`serve` (a loopback HTTP server). Adapt profiles to your project's build tools. The agent
cannot supply arbitrary shell strings. Every code execution requires explicit approval
because project code has your Windows user's permissions, beyond its working directory.
Background commands are stopped when the task ends; readiness must be verified separately.

Examples:

- “Inspect the files in demo, fix its failing tests, run the test profile in demo and show the Git diff.”
- “Open https://example.com, save its title to example-title.txt and read it back.”
- “Launch Notepad, enter a short note, save it under the approved workspace and verify the file.”
- “Start the serve profile in web, open http://127.0.0.1:8765, inspect the page and save a report.”

Type `APPROVE` only after reviewing the exact action. EOF or any other answer denies it.
Approvals cannot be supplied by the model, a page, or a repository instruction.

## Emergency stop and security boundaries

Press **Ctrl+C** in the launch terminal, or run `./stop.ps1` from another terminal. The
supervisor polls a stop latch and uses a Windows Job Object to terminate its agent process tree, including a blocked
model request. PyAutoGUI also keeps its corner fail-safe enabled. After inspecting partial
changes, clear the latch with `python -m local_agent resume`; this does not restart a task.
Stopping cannot undo completed actions or stop unrelated existing processes.

Browser sessions are isolated and service workers/WebSockets are blocked. Browser clicks,
fills, downloads, non-read HTTP methods, desktop input, overwrites, code execution and Git
actions require confirmation. An allowed site's GET requests can still have side effects;
only allow origins you trust for navigation. Untrusted content is tagged as data and never
loaded into the system prompt. This is defense in depth, not proof against prompt injection.

File tools reject escapes, credential directories, device paths and hardlinks. The system
is **not an OS sandbox**: approved code, desktop applications and race conditions in files
shared with other processes can exceed these logical boundaries. Use disposable projects
and a separate Windows account/VM for hostile code. No unrestricted execution mode exists.

Audit logs in `.runtime/state/audit.jsonl` contain tool names, timestamps, argument hashes
and status, not raw prompts, file contents, output or secrets. Console redaction is best
effort; avoid giving the agent credentials. Screenshots are transient observations and
may remain in the state directory after a crash. Review and remove them locally as needed.

## Tests and troubleshooting

```powershell
.\scripts\validate.ps1                          # Core; live checks explicitly skipped
.\scripts\validate.ps1 -Browser                 # Real local and public browser checks
.\scripts\validate.ps1 -Model                   # Includes real model-generated coding and verification
.\scripts\validate.ps1 -Browser -Model          # Adds real model/GPU/vision/unified checks
.\scripts\validate.ps1 -Desktop                 # Moves focus and types in Notepad
```

The model flag also runs a disposable counter bug-fix task: the configured local model must
observe a failing test, edit code, generate regression tests, rerun tests and review the diff.
The test executes generated Python with your Windows user permissions; no real project is
edited or committed. Missing inference/model access fails this opt-in, rather than skipping.
Run just this gate with `LOCAL_AGENT_MODEL_TEST=1` and
`python -m unittest tests.test_coding_acceptance -v` in the project environment.

The desktop test must run in an unlocked, interactive Windows session. It may leave the
test Notepad window open. The adapter identifies a new visible window by executable identity
and includes Store Notepad handoff logic. Its selection logic and normal-session Notepad
typing/save/readback pass; wider UI controls still require acceptance. Missing dependencies cause opt-in live tests to fail,
not to be reported as successful.

Socket error `10013` indicates the managed environment blocked installation network access;
`ERR_NAME_NOT_RESOLVED` blocked public browser validation here. Run setup in an authorized
network-enabled environment. `10061` at port 11434 means no local Ollama server is listening.
Missing Chromium: rerun its installation or choose Edge. Out of GPU memory: close other GPU
applications, reduce `model.context` from 8192 to 4096, then rerun GPU/tool/vision checks.

## Models and extensions

Change `model.name` and pull that model with `pull-model.ps1 -Model <tag>`. Qwen3.5 9B is the
initial candidate; official metadata advertises tools and vision, but local reliability
must pass the live tests. Measured context/residency trials are documented above; comparisons
with alternative models and broader autonomous coding quality remain open.
Check `/api/ps` evidence for `size_vram` after inference; driver availability alone is not
proof of inference acceleration.

Add an adapter method and register it in `local_agent/tools.py`. Keep schemas narrow, validate
paths and origins through `Policy`, confirm side effects, and add meaningful denial and
integration tests. Framework selection and official sources are in [docs/architecture.md](docs/architecture.md).
