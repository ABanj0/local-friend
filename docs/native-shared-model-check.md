# Installed Studio: preserve an independent Ollama service

This operator-only P0-05 check observes the actual installed application. It checks that
normal Studio closure leaves an independently running Ollama service alive and healthy.
It does not submit tasks, load models, change configuration, or download anything.

## Run in normal Windows PowerShell

Finish the current screenshot/preview check, finish or cancel active tasks, and close Studio
normally. From `C:\path\to\local-friend` run:

```powershell
.\.venv\Scripts\python.exe .\scripts\native-shared-model-check.py --exercise
```

Follow these two console prompts; type the words in **PowerShell**, not Studio:

1. Wait for the test Studio to show **Connected locally**, then type `CONNECTED`.
2. Close the test Studio using **X**, then type `CLOSED`.

You do not need to start another model terminal. If a recognizable, healthy Ollama service
already listens on `127.0.0.1:11434`, the check uses it without owning or stopping it.
Otherwise it starts an independent fixture using the installed configuration's existing
Ollama executable/model directory. That fixture belongs to a separate process job from
Studio. After verifying that it survived Studio closure, the check stops only its fixture.
An existing service remains untouched. The check never stops unrelated Python processes.

The default deadline is 180 seconds (`--seconds` accepts 60–300). On completion, failure
or interruption, cleanup attempts both separately owned process jobs. No elevated privileges
are needed. The installed configuration/history stay in use; a separate temporary WebView
profile is retained under the report directory. No production database is copied or changed
by the operator script itself; Studio performs its normal startup/reconciliation.

## Acceptance and limitations

The JSON report is written under `.runtime/native-shared-model-<id>/report.json`.
A passing exercise requires:

- Installed native/backend hashes match the existing release manifest.
- Exactly one observed backend root launch, an owned listener, and owner-confirmed connection.
- Ollama's PID **and creation time** identify a service outside Studio's descendant tree.
- Before and after normal Studio closure, the same process owns the same literal loopback
  listener and answers a bounded, fixed `GET /api/version` health check.
- Captured Studio descendants exit before the operator's cleanup runs.
- Both owned process jobs clean up successfully; no raw output/credentials are exported.

The report separates owner UI observations from independent process/listener checks.
Fixture/unit tests of this script do not certify the native application. Health is not
inference or model-quality verification. This experiment does not prove upgrade/uninstall,
screen capture, every active task effect, or general protection against hostile same-user
processes. Only the default literal model endpoint is supported by this operator experiment;
this does not change application endpoint support.

Without `--exercise`, preflight never launches Studio/Ollama and cannot pass native acceptance.
`existing_studio_preserved` means close the current Studio normally before retrying.
`backend_port_unavailable` means inspect port 17861; do not stop an unrelated listener.
`unrecognized_model_listener` or `model_listener_ownership_changed` means ownership could
not be established safely; inspect the service rather than killing it. A package mismatch,
missing dependency/configuration, missing owner confirmation, inaccessible native desktop,
or deadline remains blocked. Keep the failed report and correct the reported prerequisite.
