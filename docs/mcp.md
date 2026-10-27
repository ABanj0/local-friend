# Read-only project MCP provider

Install the optional pinned SDK in the application environment:

```powershell
uv sync --extra automation --extra desktop --extra dev --extra bundle --extra mcp
```

Add this optional section to your trusted `agent.toml`, then restart Studio:

```toml
[mcp]
project_read = true
timeout_seconds = 15
```

The coding and unified profiles now expose `mcp_project_read(path="counter.py")`.
It reads an existing UTF-8 file (maximum 8,192 bytes) in the selected project.
The browser/desktop profiles cannot call it. Disabled is the default; existing
tools, API authentication and approvals are unchanged. There is no new HTTP API.

Each call launches the shipped `local-work-agent-project` version 1 stdio server,
performs the official SDK initialization, lists and compares its exact reviewed
tool descriptor, then calls `read_text`. Server descriptions and file contents
never become instructions or permission grants. Secrets matching existing
redaction rules are removed before transmission; redaction is best effort.

Only this server is supported. There are no configurable executables, arguments,
URLs, environment variables or model-supplied tool registrations. Schema/identity
changes fail with `MCPReviewRequired`: review the package and contract together;
there is no automatic acceptance or retry. Missing/mismatched SDK versions report
the pinned extra needed without affecting ordinary disabled operation.

The host and server both check the existing file policy, with strict link checks,
credential/dependency/state exclusions and stable file identity/hash checks.
Frames and total traffic are bounded before SDK parsing. Errors contain fixed
messages; server stderr is discarded, not placed in user logs. Cancellation,
timeouts and errors stop only the owned server process tree. Nothing is replayed.
Windows Job Objects manage lifetime; this is not an operating-system sandbox.
The stdio provider requires native subprocesses. The uv lock targets Windows/Python
3.12, matching the existing setup scripts and frozen runtime. Other source-install
targets need separate dependency resolution and validation.
`uv.toml` records exact-version dependency metadata copied from the installed
SDK environment's wheel metadata. This lets uv resolve from the available local
cache without downloading another platform's wheel solely to inspect metadata.
No requirements or extras are removed. Refresh/remove these metadata entries
when upgrading those packages in a network-enabled environment, then regenerate
`uv.lock` and rerun validation. `uv lock --check --offline` verifies consistency.

The integration uses the [official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
session and server APIs. Its bounded custom stdio transport implements pipe framing,
not a replacement protocol/session implementation.

Run `python -m unittest tests.test_mcp -v` for real stdio and negative contract
checks. The optional extra is required for integration tests; skipped SDK tests
do not establish compatibility. Frozen backends must be rebuilt with the extra
installed; an older executable cannot gain MCP support from a Python install.
