# Installed native recovery check

Verified owner run (2026-10-27): report
`.runtime/native-recovery-e7420e8c254e4ef59feb27380e4dc20f/report.json` passes this scope,
with measured retry-gap lower bounds1.094892/2.019097/4.047970 seconds. Manual native
connection and normal-close/Python preservation are confirmed. Combined lifecycle evidence
closes P0-05 first; installation/upgrade and the other remaining native flows are separate.
The instructions below remain available for future regressions; no repeat is currently needed.

This operator-only check measures the remaining P0-05 retry/fallback path in the actual
installed application. It is not an agent tool or HTTP endpoint. It does not submit tasks,
change configuration, download models, rename executables, or terminate existing instances.

## Run from normal Windows PowerShell

Finish or cancel any current task, then close installed Studio. From `C:\path\to\local-friend`:

```powershell
.\.venv\Scripts\python.exe .\scripts\native-recovery-check.py --exercise
```

The check opens its own installed Studio window and temporarily reserves **127.0.0.1:17861**.
Startup failures mentioning the occupied port are intentional. The guard never accepts or
reads requests. It uses exclusive binding rather than `SO_REUSEADDR`; see
[Microsoft's socket ownership guidance](https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse).

Follow the three console prompts; type the words in **PowerShell**, not Studio:

1. Wait until the console requests `FALLBACK`. Check Studio displays the occupied-port
   error and **Restart backend**, then type `FALLBACK` in PowerShell.
2. The check releases its port guard. Click **Restart backend** in Studio. Once its status
   says **Connected locally**, type `CONNECTED` in PowerShell. Do not submit tasks.
3. Close this test Studio using **X**, then type `CLOSED` in PowerShell.

The entire exercise has a 240-second deadline (`--seconds` accepts 60–300). It releases its
guard and cleans up only its own launched processes on failure, interruption or completion.
Its separate Python fixture must survive normal Studio closure before the fixture is cleaned up.
Your normal installed configuration/history remain in use; the temporary WebView profile
is retained under the report directory rather than deleted recursively.

## Evidence and limits

The final JSON names `.runtime/native-recovery-<id>/report.json`. A passed exercise requires:

- Installed native/backend hashes match the release manifest's installed-payload expectation.
- Four failed backend launches: the initial attempt and three automatic retries.
- Observed exit-to-next-start lower bounds of at least 0.85, 1.85 and 3.85 seconds, allowing
  150ms polling/clock tolerance around the configured 1/2/4-second delays.
- Six seconds without another launch, followed by an owner-confirmed visible fallback.
- One new launch after manual restart, an owned backend listener, and owner-confirmed connection.
- Normal-close exit of the captured owned descendants before harness cleanup, while the
  independent Python fixture remains alive.

Only numeric process/timing observations, binary hashes, fixed reason codes and owner
confirmations are exported. No launch credentials, environment values, chat text, screenshots,
raw stdout/stderr or HTTP bodies are saved. UI observations are explicitly owner-confirmed;
process polling can miss a very short launch, which makes the check unaccepted rather than
inventing it. The measured interval is a conservative process observation, not a JavaScript
timer trace. This check does not certify model quality, every active-work effect, upgrade,
uninstall or preservation of an independently running Ollama service.

Without `--exercise`, the command performs preflight only and cannot claim native acceptance.
If Studio is already open it returns `existing_studio_preserved`; close it normally and rerun.
A port collision with another application, mismatched package, inaccessible desktop,
missing owner confirmation or deadline remains blocked. Do not stop unrelated processes.
