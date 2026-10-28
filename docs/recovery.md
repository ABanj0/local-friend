# Complete the remaining requirements

## Current recovery checklist (2026-10-26, after native diagnostics)

MCP2.3.0 is installed and its first read-only provider is verified. Do not repeat SDK
acquisition for this checkout. See [MCP activation and checks](mcp.md).

The primary service currently lists qwen3.5:9b. Embedding retrieval still needs its
evaluated local model; follow the [semantic dependency steps](project-memory.md#semantic-retrieval-dependency-p1-03-b).
The existing pull-model script accepts a model name and does not change the active chat model.

For native startup, run the [bounded diagnostic](native-diagnostics.md) from a normal
interactive Windows PowerShell after closing Studio. The managed check observes
WebView2 GPU subprocess0xc0000022/access denial and an unusable GPU. A temporary
GPU-disabled test and a fresh OS temporary profile both failed. The exact denied
operation remains unidentified; no rendering or security defaults were changed.
The report is diagnostic evidence, not native application acceptance.

Ordinary command access works, but registry/PyPI/GitHub HTTPS still fails10013 in this
managed session despite successful DNS. NSIS installation/upgrade, configured VM
isolation and a second measured routing candidate remain separate gates. Earlier
acquisition/1909/setup histories below do not supersede this checklist.

## Earlier comparison context (2026-10-26)

The primary Ollama service works and the actual paired trial is complete: both profiles
pass56/60 tasks and8/8 safety checks. The faster candidate fails its per-case quality
gate and stays unapplied. See [the comparison report](probe-qualification.md).
Embedding acquisition remains blocked10013 in this managed command session. The SDK
acquisition blocker was resolved by the isolated cache and actual integration checks.
Continuing the goal does not change its effective network permissions. No application
source/default or client permission configuration is changed by this recovery guide.

### Command-network access and hosted tools are separate

Official OpenAI documentation distinguishes command networking from hosted search,
apps and other tools. A successful documentation search does not establish download
access for uv or an Ollama child process. Check the effective permissions with the host
owner; preserve filesystem restrictions and request only approved dependency hosts,
starting with pypi.org and files.pythonhosted.org for the SDK. Domain filtering needs
an active proxy as well as enabled command networking. Profile and legacy settings
must not be mixed; managed requirements can constrain user choices.
See [permissions](https://learn.chatgpt.com/docs/permissions) and
[agent network controls](https://learn.chatgpt.com/docs/agent-approvals-security).

If networking was already expected to work, follow the
[Windows sandbox diagnostic guidance](https://learn.chatgpt.com/docs/windows/windows-sandbox):
restart the client, check the effective policy, and retain a sanitized sandbox log if
the failure persists. An intentionally disabled network needs an owner-approved change;
repeated task resumes do not grant it. Do not switch to unrestricted access or change
firewall/ACL/account controls as an automatic dependency-install workaround.

### Earlier directory-inspection baseline (2026-10-25)

P2-03 B1 passes638 default tests with61 skipped,172 targeted and56 rebuilt-package
checks with no skips. Directory-triggered inspections are documented in
[the workflow guide](directory-inspections.md). Remaining model/SDK/native gates are
separate; a source or packaged protocol test cannot establish their completion.

### Restore model access for the next review comparison

1. Launch `./desktop-dev.ps1` from your normal unlocked Windows session. Open **Models &
   settings**, start Ollama through the existing control if needed, and check that the
   configured `qwen3.5:9b` appears. A separate model terminal is not normally required.
2. Submit a short chat. From normal PowerShell, verify the same configured service with
   `Invoke-RestMethod http://127.0.0.1:11434/api/tags`
   ([official installed-model endpoint](https://docs.ollama.com/api/tags)). Successful metadata must list the
   configured model; an empty list is not model acceptance.
3. If Studio's portable service lists no models and logs **Access is denied**, inspect
   which account owns/runs that service and which model store it is configured to use.
   The portable launcher uses `.runtime/models`; an already-running service may use a
   different store. Ask the machine/policy owner to resolve approved-account access to
   that existing store. Do not delete weights, broadly change ACLs, disable protection,
   run as administrator, or terminate unrelated services to hide the error.
4. Rerun `./scripts/validate.ps1 -Browser -BrowserChannel msedge -Model` and retain the
   terminal verdict, including skips. Keep the working normal-session service available
   so the managed implementation session can check its metadata and run the paired
   review gate. If only the managed process is denied, its policy owner must restore
   approved local access; a normal-session pass does not prove that restriction is fixed.

Fresh managed evidence: no initial listener; an owned service then started but returned
zero models and logged Access is denied. Only that owned process was closed. No model
download or inference was attempted. See `.runtime/p2-04-review/owned-model.json`.

### MCP dependency check; isolated setup only for a fresh environment

The verified SDK/client/type version is2.3.0. Check the application environment first:

```powershell
.\.venv\Scripts\python.exe -c "from local_agent.mcp_provider import require_sdk; require_sdk(); print('Pinned MCP dependencies available')"
```

If it succeeds, skip acquisition and use [mcp.md](mcp.md). That guide includes the full
application extras when resyncing; do not discard working desktop dependencies by syncing
only one extra. Actual source/frozen handshake/list/call/cancellation and scoped-provider
checks have already passed; historical unverified-candidate statements no longer apply.

Only for a new or incomplete probe environment, use ordinary network-authorized PowerShell:

```powershell
Set-Location C:\path\to\local-friend
if (!(Test-Path .runtime\mcp-sdk-probe)) {
    uv venv --python .venv\Scripts\python.exe .runtime\mcp-sdk-probe
    if ($LASTEXITCODE -ne 0) { throw 'Isolated SDK environment creation failed.' }
}
if (!(Test-Path .runtime\mcp-sdk-probe\Scripts\python.exe)) {
    throw 'Existing probe directory is incomplete; inspect it before modifying it.'
}
uv pip install --python .runtime\mcp-sdk-probe\Scripts\python.exe --cache-dir .runtime\mcp-sdk-cache mcp==2.3.0
if ($LASTEXITCODE -ne 0) { throw 'SDK acquisition failed; retain the console output.' }
& .\.runtime\mcp-sdk-probe\Scripts\python.exe -c "from importlib.metadata import version; import mcp; assert version('mcp') == '2.3.0'; print(version('mcp'))"
if ($LASTEXITCODE -ne 0) { throw 'SDK import/version verification failed.' }
```

Keep the probe environment/cache in the workspace for dependency recovery. This command
installs into the separate probe; the application check above still applies. A fresh
installation alone does not verify an adapter. If download also fails10013, have the
network/policy owner restore ordinary approved package access. Do not disable security
controls or alter the application's dependencies to force resolution.
The commands use uv's [interpreter/environment options](https://docs.astral.sh/uv/reference/cli/#uv-venv)
and [explicit cache directory](https://docs.astral.sh/uv/concepts/cache/), also checked
against the installed CLI help. Do not edit uv's cache files manually.
The snippet preserves an existing incomplete directory, stops on setup/install failure
and checks the pinned import. Previously closed integration evidence is at
.runtime/p2-02-mcp-integration/validation.json; repeat relevant checks after dependency changes.

Windows command access currently works; historical1909 reports below are retained.
Interactive desktop/native installer/VM/second-model gates still need their respective
approved environments. Skipped tests remain unverified.

## Windows error 1909: execution account lockout

### Recurrence verified on 2026-10-23

The managed command runner again failed before PowerShell started:
`CreateProcessWithLogonW failed: 1909`. The earlier successful probes above are
historical evidence, not the current managed-runner status.

An explicitly approved execution outside the sandbox successfully read the workspace
and wrote/read back this documentation update. This provides an approved route for
these documentation edits; it does not establish recovery of the managed account.
Use that route only with tool approval. Do not change repository ACLs or account
security settings to address a failure that occurs before the process starts.
Managed-runner recovery and recurrence prevention remain unresolved.


Error 1909 (`ERROR_ACCOUNT_LOCKED_OUT`) means Windows rejected a logon because
the referenced account is locked out; it is not evidence of a repository file
permission problem. See [Microsoft's error reference](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1700-3999-).

Verified on 2026-10-23: fresh managed commands run as `ANGELO\CodexSandboxOffline`.
The current machine policy reports a threshold of 10 failed logons, a 10-minute
lockout duration, and a 10-minute observation window. Separate PowerShell launches
and a workspace Python child-process/file-create/write/read/cleanup probe passed.
The previous blocker has cleared; no account reset or security-policy change was
needed. The original failed logon source and recovery mechanism remain unverified.
The queried Security log returned no matching 4740 events for the preceding two
days; WMI account-lockout inspection was denied in the restricted session.

If it returns:

1. Stop automated retries and preserve the exact error and timestamp. If Windows
   cannot start the tool process, project code cannot repair that startup failure.
2. Let the configured lockout duration elapse without repeated login attempts.
   This machine currently reports 10 minutes; check `net accounts` from a normal
   terminal if policy has changed.
3. Retry one harmless workspace command. If it still fails, save work and restart
   the Codex application, then retry once. This is a diagnostic recovery step,
   not a guaranteed fix for stale managed-account credentials.
4. If it persists or recurs, ask the machine administrator and Codex support to
   investigate the managed sandbox account provisioning and Windows Security
   events 4740/4625 at the captured timestamps. Any manual unlock or account repair
   requires administrator approval. Do not reset sandbox passwords, delete sandbox
   credential directories, disable the sandbox, or weaken account-lockout policy.

Do not mark this as permanently fixed based only on successful probes. Current
execution and file access are verified; prevention of recurrence is not.

**Historical setup status:** dependencies and the model were installed. Real model/GPU/tool/vision
and combined browser/file tests pass after the controller fix. Steps 1–4 below are setup
reference, not instructions to reinstall. Rerun step 6 for the repaired Notepad launch;
public DNS and full desktop acceptance remain unresolved. See IMPLEMENTATION.md for results.

The system is **not fully accepted**. The original checks showed blocked outbound sockets
(`10013`), no Ollama listener (`10061`), missing isolated automation packages, and zero
accessible desktop windows. Core tests: 28 passed, 10 explicitly skipped.

Run these steps in a normal, non-administrator PowerShell terminal on the target computer,
in an unlocked interactive desktop session with authorized network access. Do not disable
firewall, antivirus, TLS checks or execution policies. This managed session cannot grant
itself network access or an interactive desktop.

## 1. Check network access and tools

```powershell
Set-Location C:\path\to\local-friend
Get-Command uv, git, python
nvidia-smi
Test-NetConnection pypi.org -Port 443
Test-NetConnection github.com -Port 443
Resolve-DnsName example.com
```

Expected: tools resolve, the GPU is listed, TCP checks return `TcpTestSucceeded : True`,
and DNS resolves. Installers may need additional download/CDN hosts shown in their errors.
If access still fails in this ordinary terminal, ask the machine/network policy owner for
approved access. Do not substitute an unverified mirror or bypass the restriction.

Optional hardware verification, previously blocked by WMI permissions:

```powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
```

## 2. Install isolated dependencies and Ollama

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import playwright, pywinauto, pyautogui, PIL; print('Automation imports OK')"
.\.runtime\ollama\ollama.exe --version
Test-Path uv.lock
```

Expected: Python 3.12, successful imports, an Ollama version, and `True` for the lockfile.
An Ollama warning about a server not running is expected before step 3. Setup may replace
the generated Python 3.14 `.venv`; it does not replace source code or `agent.toml`.
Retain `uv.lock` and `requirements-installed.txt`. For subsequent dependency restoration:

```powershell
uv sync --locked --extra automation --extra dev
```

If Chromium download fails, resolve the CDN restriction and rerun setup. Installed Edge
is an alternative for browser testing, but setup currently stops before Ollama installation
when Chromium installation fails. Do not assume its later steps completed. A missing release
checksum or checksum mismatch requires inspection of the official release, not skipping
integrity verification. If scripts are blocked, follow your organization's approved signing
procedure; do not change execution policy to bypass controls.

## 3. Start the local model

In **terminal A**, leave this running:

```powershell
Set-Location C:\path\to\local-friend
.\scripts\start-model.ps1
```

In **terminal B**, in the same directory:

```powershell
.\scripts\pull-model.ps1
Invoke-RestMethod http://127.0.0.1:11434/api/tags
.\.venv\Scripts\python.exe -m local_agent doctor
```

Expected: `qwen3.5:9b` is listed, dependencies are present, and doctor exits 0.
If port 11434 is occupied, identify the existing listener before proceeding:

```powershell
Get-NetTCPConnection -LocalPort 11434 -State Listen | Select-Object LocalAddress, OwningProcess
```

Do not kill unidentified processes. Deliberately choose an existing Ollama server or stop
it normally and use the project server. The server determines where weights are stored.

## 4. Verify inference, GPU, tools and vision

```powershell
.\scripts\validate.ps1 -Model
Invoke-RestMethod http://127.0.0.1:11434/api/ps | ConvertTo-Json -Depth 6
```

Pass criteria: structured-output, real tool-call/write/readback and vision tests pass;
the selected model has `size_vram > 0`. The combined browser/model test is intentionally
skipped until step 5. A text reply or `nvidia-smi` alone does not satisfy these requirements.

For out-of-memory errors, reduce `model.context` in `agent.toml` from 8192 to 4096, close
your own unused GPU-heavy applications, and rerun the same tests. If GPU allocation is zero,
inspect server errors and driver status. Preserve actual tool/vision failures for diagnosis;
do not replace those checks with a text-generation test.

For tuning, record model tag, quantization, context, GPU allocation and elapsed test time
for each setting. Confirm alternative tags in the official registry before pulling them,
then repeat all live tests after changing `model.name`. No best-performing model has yet
been measured on this machine.

## 5. Verify public browsing and autonomous coordination

```powershell
.\scripts\validate.ps1 -Browser -Model
```

With installed Edge instead of Chromium:

```powershell
.\scripts\validate.ps1 -Browser -Model -BrowserChannel msedge
```

Expected: public-site/form checks pass and `test_unified_live_model_browser_and_files`
passes, not skips. It requires the real model to open the fixture, write its title and
read it back. For `ERR_NAME_NOT_RESOLVED`, test DNS and the same URL in your normal browser;
resolve the underlying network issue through its owner. For a policy-denied origin, add
only the intended exact origin to `browser.allowed_origins`, not a wildcard.

## 6. Verify the interactive desktop

Save unrelated work first. Keep the session unlocked and do not type or move focus during:

```powershell
.\scripts\validate.ps1 -Desktop
```

Expected: Notepad launches, sample text is typed, a new temporary workspace file is saved
and its contents are verified. Imports alone do not demonstrate desktop functionality.
Close only the test Notepad window afterward if it remains open.

If no windows are accessible, use your logged-in desktop terminal rather than a locked
session, service or headless runner. If Store Notepad launches but the adapter cannot find
its window, this is an outstanding compatibility bug. Gather the exception and:

```powershell
Get-Process Notepad -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle, Path
Get-AppxPackage Microsoft.WindowsNotepad | Select-Object Name, Version
```

The adapter then needs repair to identify the newly launched owned window safely, followed
by another acceptance run. Do not attach to arbitrary existing windows or personal documents.
UIA controls/menus, screenshots and coordinate input also require live validation; the
Notepad typing test does not certify every desktop tool.

## 7. Finish development and security acceptance

```powershell
.\.venv\Scripts\python.exe -m ruff check local_agent tests
.\.venv\Scripts\python.exe -m compileall -q local_agent tests
.\scripts\validate.ps1 -Browser -Model -Desktop
```

Fix failures and rerun the affected checks. All enabled live tests must pass. The symlink
test may still skip if Windows disallows symlink creation; leave that explicitly unverified
rather than requesting elevation merely to pass it.

Exercise real model-driven coding in a new disposable project:

```powershell
.\launch.ps1 "Create a new demo project under acceptance-demo. Write a Python addition function and unittest tests, run the tests, inspect Git changes, and report the observed results."
```

Review code-execution approvals. Then introduce a small arithmetic bug in that disposable
function, establish a failing test, and ask the agent to fix it. Independently verify the
final test result. Do not use an existing project for this acceptance exercise.

Prompt-injection resistance is not completed by installing dependencies. Current tests
verify policy checks and untrusted-data roles, not immunity to malicious inputs. Keep
approvals/scopes enabled. Isolation for hostile code would require additional OS sandbox/VM
design and validation. Record this limitation rather than asserting an absolute guarantee.

## 8. Update the checklist with evidence

Record commands, actual results, GPU/model evidence and remaining skips in `IMPLEMENTATION.md`.
Check off capabilities only after their relevant acceptance checks pass. Installation alone
does not establish working behavior, and new compatibility failures remain open work.

| Open requirement | Recovery step |
| --- | --- |
| Dependencies, runtime, model weights, lockfile | 1–3 |
| Inference, GPU, structured output, tools, vision | 4 |
| Measured context/model tuning | 4, comparative measurements |
| Public browser and real combined workflow | 5 |
| Notepad, desktop controls/screenshots/input | 6 |
| Lint and autonomous coding/debugging | 7 |
| Security limits and skipped path checks | 7; not automatically fixed by setup |
| Working system and final requirement sign-off | 8 after applicable checks pass |

Official installation references are linked in [architecture.md](architecture.md).
