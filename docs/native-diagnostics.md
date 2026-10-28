# Native startup diagnostic

Run this development check from a normal, non-administrator PowerShell in the checkout:

```powershell
Set-Location C:\path\to\local-friend
.\.venv\Scripts\python.exe -m local_agent.native_diagnostics --seconds 10
```

Close Studio first. The check refuses to launch if another Studio or backend is present,
or if the frontend port is occupied. It never stops those processes or reuses their ports.
It requires the existing native debug executable. If missing, build it using the native
development steps in [desktop.md](desktop.md#remaining-native-validation).

The check launches only this checkout's debug executable, uses a fresh workspace WebView
profile, and serves a harmless page on localhost1420. That page has no scripts, backend
connection, tool calls or account access. The check adds per-process logging flags and
keeps normal rendering/security settings. It does not change the caller's environment.

Read the printed `.runtime/native-diagnostic-<id>/report.json`:

- `status: observed_failure` means an actual startup failure was observed.
- `gpu_access_denied: true` means a GPU-process log contains exit code `0xc0000022`.
- `gpu_unusable: true` means WebView2 reported its GPU process unusable.
- `status: frontend_requested` means the harmless page was requested. Exit0 has only
  this scope; native application acceptance remains `not_verified`.
- `blocked` or `inconclusive` never establishes a working native application. Exit1
  is expected for these outcomes and observed failures.
- `owned_closed: false` requires reviewing that exact owned run before retrying.

Observation lasts1–30 seconds, followed by owned cleanup. Log capture stops when its
1MiB threshold is observed; reads are capped and truncation is explicit. Reports contain
bounded numeric/boolean categories, not raw logs, URLs, environment values or stdout.
Only the expected regular, single-link captured log is removed after identity checks.
Profiles and unexpected/replaced/linked files are preserved for inspection.

For the observed managed-session failure:

1. Repeat the command in your normal interactive Windows session and compare the report.
2. If the page is requested there, continue the real single-instance, recovery and
   shutdown checks in [desktop.md](desktop.md#remaining-native-validation).
3. If GPU access denial also occurs there, correlate the report's UTC time and native
   PID with Windows application/security diagnostics for WebView2. The report identifies
   a failed subprocess; it does not identify which underlying access operation failed.
4. Rerun native acceptance after resolving that environmental failure. Keep P0-05 open
   until the actual application, installer and upgrade criteria are independently tested.

Microsoft documents [WebView2 logging/environment options](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/win32/webview2-idl)
and [GPU troubleshooting/performance guidance](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/performance).
The temporary `--disable-gpu` experiment did not resolve this managed-session failure;
the helper does not apply it. A fresh standard OS temporary profile produced the same
failure. Ollama inference and WebView2 rendering are separate.

Run unit/HTTP/process checks with `python -m unittest tests.test_native_diagnostics -v`.
Set `LIVE_NATIVE_DIAGNOSTICS=1` to run the owned native diagnostic case. A passing test
validates the diagnostic report and cleanup, not successful application startup.
