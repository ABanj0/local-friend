# Owned background commands and readiness

Coding and Unified tasks can start configured development services with `start_command`,
inspect them with `command_status`, and stop them with `stop_command`. Each start requires
approval of the exact argv, project directory and configured readiness request. These are
task-owned processes: normal completion, cancellation and backend shutdown close them.
They are not persistent services, scheduled jobs or resumable sessions.

## Configure a harmless local check

The existing project configuration includes a `serve` command on loopback port 8765.
For another configuration, add this key inside its existing `[commands]` table if needed:

```toml
serve = ["{python}", "-m", "http.server", "8765", "--bind", "127.0.0.1"]
```

Append an optional readiness table to the trusted configuration:

```toml
[readiness.serve]
url = "http://127.0.0.1:8765/"
status = 200
timeout = 10
interval = 0.2
```

Restart the development backend after configuration changes. Existing user configuration
is not changed automatically. Choose a harmless public health/status path on your own
application. Ask the agent to start `serve`, inspect its status, perform the workflow and
stop it. Running this through the model requires a working local Ollama service.

Without a table, start returns **unconfigured** readiness and performs no HTTP probe.
With a table, start waits for the configured status, process exit or startup deadline.
Failed readiness closes the owned service and returns a failed tool result with bounded
diagnostics. Inspect/stop that owned entry before requesting a fresh approved start.

## What readiness means

Checks accept only ASCII HTTP URLs on literal `127.0.0.1` or `::1`, with an explicit port,
no credentials, query or fragment. Encode non-ASCII path characters. The exact expected
status must be 2xx; startup timeout is 0.1–30 seconds and polling interval 0.05–2 seconds.
Defaults are 200, ten seconds and 0.2 seconds. `psutil`, already in the desktop extra,
provides listener ownership inspection; a missing dependency fails before execution.

Every HTTP request first requires all listeners on that port to belong to the owned
process tree. Unknown ownership, insufficient inspection access or an unrelated listener
never authorizes a request. Choose another approved port if ownership is ambiguous.
Checks send GET without cookies, credentials or proxies; they read no body and follow no
redirect. Socket inactivity and total HTTP-probe lifetime are bounded, including dripping
headers. Host system calls/scheduling can add latency; existing worker deadlines and
emergency stop remain the outer boundary.

**Ready observed** records an HTTP/ownership observation and timestamp, not application
correctness. After initial readiness, process liveness/output remain monitored; HTTP is
rechecked when `command_status` is requested. Timeout/exit/stop is distinct from the last
successful observation. PID checks are point-in-time logical controls, not OS isolation.

## Output and lifecycle

Up to four background commands can be owned by one task. Output shares the foreground
16,000-byte raw/display prefix, streaming redactor and 64-event budget. Background state
has at most 256 bounded updates per instance. Studio shows recent commands plus up to four
active owned servers in the selected conversation, including last-check diagnostics and
last-ready timestamps. Existing durable replay restores observations without restarting work.

Windows Job Objects close owned descendants and inherited output pipes. A hard worker
termination may omit final metadata; Studio marks an interrupted outcome. Prior side effects
are not undone. Separate test-run/artifact verifiers remain necessary. No administrator
privilege, arbitrary URL/PID tool argument or new public command endpoint is introduced.

Run `python -m unittest tests.test_background -v` in the project environment. These exercise
real IPv4/IPv6 servers, ownership denial, timeout/early exit, trickling headers, bounded logs,
faults and owned cleanup. Enable `LIVE_STUDIO_UI=1` for `tests.test_tool_profile_ui`; model
replies there are explicit fixtures, while server/probe/process/UI actions are real. Current
live-model, native WebView and installer gates remain separate.

Implementation uses the existing [psutil connection APIs](https://psutil.io/) and
[Python HTTP client](https://docs.python.org/3.12/library/http.client.html), without another framework.
