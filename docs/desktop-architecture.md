# Desktop architecture

The desktop wraps the working synchronous agent; it does not replace the tools or CLI.
Tauri owns one Python backend and an ephemeral credential. HTTP uses bearer authentication;
WebSockets authenticate in their first message, with an origin allowlist and a timeout.
No tokens are put in URLs, logs or SQLite. FastAPI binds to 127.0.0.1 only.

Each task runs in a spawned process, keeping synchronous Playwright/UI Automation off the
server event loop. The manager owns its process handle and Windows Job Object. A duplex
pipe carries events and action-specific approval replies. Cancel terminates only the owned
task tree. Worker exit without a result becomes a visible failure. Backend restart marks
unfinished tasks interrupted, never silently re-executes them. Pause/resume is unsupported
because the existing agent cannot restore browser/desktop state safely.

SQLite stores conversations, messages, task summaries, redacted events and project IDs.
Approved project roots are limited to directories under the configured workspace; selecting
a directory outside that root is rejected. The agent cannot change its scopes through tools.
The UI exposes policy and pending approvals rather than an unauthenticated command endpoint.

Direct chat streams Ollama chunks; agent runs preserve the existing plan/tool/result loop.
Screenshots and command outputs are real observations, not simulated previews. Screenshots
are transient and sensitive; event persistence excludes image payloads. Browser login uses
a visible isolated browser with an explicit human-intervention tool, not stored credentials.

Production packages a PyInstaller sidecar through Tauri's externalBin mechanism. Development
starts the existing .venv interpreter. Ollama is reused when already running; only a server
started by this application is owned and eligible for shutdown. No process-name-wide kills.

Sources reviewed:

- https://v2.tauri.app/start/prerequisites/
- https://v2.tauri.app/develop/sidecar/
- https://v2.tauri.app/plugin/single-instance/
- https://v2.tauri.app/plugin/dialog/
- https://fastapi.tiangolo.com/advanced/websockets/
- https://tailwindcss.com/docs/installation/using-vite

The toolchain and package installation are currently blocked in the managed execution
environment. Source implementation and backend-core tests must be distinguished from a
compiled desktop application and its end-to-end acceptance.
