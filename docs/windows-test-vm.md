# Separate Windows VM for release acceptance

Status: **P0-05 native install/upgrade/retention/uninstall acceptance passed2026-10-28**.
The actual Standard-user guest runs the installed app, real WebView IPC/backend/Ollama and
native controls. The0.1.0â†’0.1.1 test upgrade preserves146 original logical records/config;
default uninstall/reinstall preserves162 current records and real inference works afterward.
Explicit native delete-data uninstall removes both Studio data roots and its default
workspace; outside canaries/source and independent Ollama survive. Final Studio/helper
processes, fixture tasks and debug listeners are absent. The guest intentionally ends with
Studio uninstalled; evidence/backups remain in StudioTest's dedicated acceptance directory.
Host production installation/history are untouched. See IMPLEMENTATION.md and
`.runtime/p0-05-vm-acceptance/validation.json` for exact scope, failures and evidence.

Addresses and host account names below are illustrative replacements for private test values.

Environment history: on 2026-10-28, Hyper-V's `New-VM` and `Get-VM` commands are
available and `vmms` is running. Managed-session `Get-VMHost`, `Get-VM` and `Get-VMSwitch`
all return **Access denied**. The owner supplied the ISO; its duplicate `.iso.iso` extension
was corrected to `.runtime/windows-vm/Windows11.iso` (9,047,330,816 bytes). The owner has
since created the VM, recovered from the DVD boot failure, confirmed its window title and
Windows desktop, and reports signing into StudioTest. These are owner observations;
later key-only SSH independently verifies StudioTest is a Standard user, the installed0.1.0
payload hashes, Ollama/model metadata and the approved14-byte artifact. Later automated
native/upgrade/uninstall testing completes the matrix below. Initial clean setup/install
includes owner observation; subsequent identities, state and matrix are independently read.
No VM has been created by this agent.
The owner requested a separate VM. This guide uses Hyper-V so the existing Studio
installation/history stay in the host account. It does not implement P1-07 agent isolation.

## 1. Enable Hyper-V on the host

### Host management permission, separate from guest SSH

Example operator token is `EXAMPLE-PC\ExampleUser`, without active Administrator or Hyper-V
Administrators membership. Guest SSH as StudioTest still works. Hyper-V provider commands
are rejected on the physical host; guest credentials cannot supply that permission.

If the owner chooses direct management, run this once in **Administrator Windows
PowerShell on the physical host, outside the VM**:

```powershell
Add-LocalGroupMember -SID 'S-1-5-32-578' -Member 'EXAMPLE-PC\ExampleUser'
```

Replace the example account with your own verified host account. The command normally
prints nothing. Save work, sign out of Windows fully, sign back in and reopen the coding
session so its token receives the group. Verify actual `Get-VM -Name 'Studio-Release-Test'`
before claiming access. This grants management of all local Hyper-V VMs, not just the
release fixture. The alternative is to keep permissions unchanged and have the owner run
reviewed, specific host management commands. Do not run the whole agent as administrator.
No membership change has been executed by the agent.

See [Microsoft's Hyper-V permission guidance](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/plan/plan-hyper-v-security-in-windows-server)
and [Add-LocalGroupMember](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.localaccounts/add-localgroupmember?view=powershell-5.1).

### Feature setup, only if missing

Open **PowerShell as Administrator** in your normal Windows session and run:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All -NoRestart
```

Save your work and restart Windows if the command reports `RestartNeeded : True`.
Then reopen administrator PowerShell and check `Get-Command New-VM`.
If that command already succeeds, do not repeat feature installation. Check `Get-VM`
and `Get-VMSwitch` in that normal administrator session. If those work while the managed
session reports Access denied, perform the creation block below in the normal session;
report its result and the ISO's full path. Command availability alone does not verify VM
provider access. Do not change access controls to bypass the managed-session boundary.
If firmware virtualization is disabled, resolve that prerequisite first. Do not disable
Windows security controls. See [Microsoft's Hyper-V installation guide](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/install-hyper-v).

Download an x64 Windows 11 ISO from [Microsoft's official download page](https://www.microsoft.com/en-us/software-download/windows11).
Use installation media/licensing appropriate to this guest. Save it as
`C:\path\to\local-friend\.runtime\windows-vm\Windows11.iso`, or pass its actual path with `-IsoPath`.
No Windows ISO has been downloaded automatically. Sandbox is a separate option, but its
default administrative account does not establish our standard-user acceptance criterion;
see [Microsoft's Sandbox account documentation](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file).

## 2. Create a new VM

Run in your normal **Administrator PowerShell**. This creates only the named new VM and its new disk;
existing VM names/directories are refused. `Get-VMSwitch` must show an existing
**Default Switch**; otherwise stop and choose the intended network configuration first.

```powershell
cd C:\path\to\local-friend
.\scripts\new-windows-test-vm.ps1
```

The script configures `Studio-Release-Test`: Generation 2, 16 GB RAM, four virtual CPUs,
a new dynamic 128 GB disk, Secure Boot, virtual TPM and the installer DVD. It opens Virtual
Machine Connection with the VM **off**, so the brief DVD keypress prompt is not missed
while the console opens. Click **Start**, click **inside that window** and press Space
when prompted. Run Windows Setup there; do not open the ISO's setup.exe on the host.
For a different ISO location, pass `-IsoPath 'C:\path\Windows11.iso'`.

Generation 2, Secure Boot and virtual TPM follow
[Microsoft's Windows 11 VM guidance](https://techcommunity.microsoft.com/blog/itopstalkblog/how-to-run-a-windows-11-vm-on-hyper-v/3713948).
If creation partially fails, retain the named VM/disk and report the failing command;
do not rerun the creation block over them or delete unrelated VMs.

### If the DVD boot loader fails

A missed "Press any key to boot from CD or DVD" prompt can produce the firmware's boot
failure summary. In the existing VM console, choose **Restart** and immediately click
inside the display and tap Space repeatedly until Windows Setup appears. Do not rerun the
creation script or recreate the disk. This is a recovery attempt, not proof of the cause.

If it still fails, inspect the VM in normal Administrator PowerShell:

```powershell
Get-VMDvdDrive -VMName 'Studio-Release-Test' | Format-List Path,ControllerNumber,ControllerLocation
Get-VMFirmware -VMName 'Studio-Release-Test' | Format-List SecureBoot,SecureBootTemplate,BootOrder
```

The DVD path should reference the supplied ISO. Retain the output to diagnose image,
boot-order or firmware errors before changing settings. Do not disable Secure Boot as a
generic workaround. The empty disk and absent network boot image are expected before
Windows installation; the DVD boot is the first issue to resolve.

## 3. Prepare the guest account and dependencies

Install Windows onto this VM's new virtual disk. Complete Windows setup interactively.
Inside the guest, create a separate **Standard user** account, sign into it, and run Studio
and its installer there without elevation. An unelevated administrator account is not the
same acceptance condition as a standard user. Keep guest credentials private.

Install the documented WebView2, Ollama, Python and browser prerequisites **inside the guest**.
For the packaged application, do not run the development setup or install Node/Rust/build
tools. While signed into StudioTest, use Edge to download the Windows installer from
[Ollama's official download page](https://ollama.com/download/windows) and run it normally.
Ollama supports per-user installation without administrator rights; see
[its Windows documentation](https://docs.ollama.com/windows). This installs the runtime,
not the selected model. Windows 11 normally provides Edge; verify WebView2 availability
when installing Studio. A separate Python runtime is needed for Python command/test
workflows, not for the first chat and approved text-file creation checks.
Keep Ollama bound to the guest's localhost. Provide the selected model through an approved
local copy/download; host localhost is not the guest's localhost. No host-service public
bind or firewall exception is needed. Do not claim guest GPU acceleration without observing it.
Start with guest CPU inference; the VM has 16 GB RAM and four virtual processors.

After running the Ollama installer, open a new **normal PowerShell inside the VM**:

```powershell
ollama --version
ollama pull qwen3.5:9b
ollama list
```

Latest owner report: guest Ollama is **0.40.12**, with an **empty model listing**. The
runtime is installed; model download/inference remain pending. This is owner-provided
evidence, not independent managed-session guest inspection.
Retain the version, successful pull and local model listing before claiming readiness.
These use the [documented local CLI](https://docs.ollama.com/cli). Do not choose a cloud
model or change the host Ollama listener. The guest's current runtime/model versions have
not been independently observed. If `ollama` is not recognized, first check the install
completed in StudioTest and reopen PowerShell; retain the exact error rather than changing
global PATH or privileges.

Take a clean guest checkpoint before Studio installation. Copy only the two fixture
installers and intended test inputs into the guest; avoid exposing the host repository,
production state, credentials or broad writable host folders. Use a deliberate transfer
method appropriate to your VM session. Export only benign test evidence afterward.

### Prepared transfer disc

The host file `C:\path\to\local-friend\.runtime\p0-05-vm-transfer\studio-test.iso` is a
148,260,864-byte **data disc**, not Windows installation media. It contains only
`setup010.exe`, `setup011.exe`, `checksums.json`, `README.txt` and
`Check-BeforeInstall.ps1`. Both EXEs are exact copies of the retained installers, renamed
for convenience. Every file has been independently read back from the ISO and hashed;
the image SHA256 is `f1842456b3bdd29ef2b4f1dd2a75165d07b0786e1acb584368cc3b106563ceb5`.
There are no host credentials, model weights or private configuration/history on it.

After Windows is installed, attach it to the existing VM's DVD drive from **host
Administrator PowerShell**. This changes only that VM's mounted DVD; it creates no share:

```powershell
cd C:\path\to\local-friend
$discPath = (Resolve-Path -LiteralPath '.runtime\p0-05-vm-transfer\studio-test.iso').Path
$dvd = @(Get-VMDvdDrive -VMName 'Studio-Release-Test' -ErrorAction Stop)
if ($dvd.Count -ne 1) { throw 'Expected exactly one test VM DVD drive; preserve existing configuration' }
$dvd[0] | Set-VMDvdDrive -Path $discPath -ErrorAction Stop
```

This attachment is **not yet executed or verified** by the agent because managed provider
access is denied. In guest File Explorer, open **This PC â†’ STUDIO_TEST DVD**. Use that
actual drive letter when running the observer (for example `D:\Check-BeforeInstall.ps1`)
in normal guest PowerShell. The observer only reports account/Studio-footprint booleans;
it changes nothing and rejects an administrator-group account even when unelevated.
Require `account_is_StudioTest` and `standard_user` true and all three Studio-footprint
fields false before clean installation. Do not weaken script execution policy if blocked;
retain the error for a supported alternative. Verify copied installers with `Get-FileHash`
and `checksums.json`, then run **setup010.exe first**, normally. Reserve setup011.exe for
the later actual upgrade. The README contains the remaining evidence sequence.

## 4. Execute the install/upgrade matrix

This matrix was executed successfully2026-10-28. Repeat for relevant packaging/application
changes, using a fresh approved fixture. Temporary interactive-token tasks used Standard
user RunLevel0 and were removed afterward. Real WebView2 CDP automation used child-only
loopback debugging arguments; no mocked IPC, public debugger, permanent browser settings
or replacement model. Restore CDP's default download behavior before testing actual native
Downloads delivery. Raw database/config backups stay in the guest fixture outside app data.
The automation approach follows [Playwright's WebView2 guide](https://playwright.dev/python/docs/webview2)
and [Microsoft's interactive-token task security rules](https://learn.microsoft.com/en-us/windows/win32/taskschd/security-contexts-for-running-tasks).

SSH status (2026-10-28): after the owner permission change and exact public host-key
fingerprint comparison, key-only SSH login as StudioTest succeeds with Standard-user group
membership verified. The temporary credential/configuration is isolated under
`.runtime/p0-05-vm-ssh/`; private keys are never transfer-disc/archive inputs. The obsolete
guest test key has been revoked and fresh login verified. Native/backend payload hashes,
Ollama0.40.12/local9B digest and the approved artifact's exact bytes/hash are now read back
directly. Read-only evidence is retained in guest-readonly-evidence.json. No complete native
UI/upgrade/uninstall or P1-07 agent-isolation capability is inferred from SSH.

Earlier SSH investigation (superseded at transport/authentication scope): owner confirms OpenSSH installed/running with a
successful guest loopback test and listener0.0.0.0:22. The existing inbound rule was
Private-only and restricted to host192.0.2.1. After scoped profile adjustment, actual
normal-host TCP22 to guest192.0.2.2 succeeds. This managed session still receives
connection Permission denied before SSH authentication. No key login or remote execution
has been verified. Keep the host-only firewall restriction; another guest rule change is
not indicated by the successful normal-host test.

The session needs approved command-network access before remote automation can replace
manual checks. See [OpenAI's Windows sandbox guide](https://learn.chatgpt.com/docs/windows/windows-sandbox)
and [permission/network configuration](https://learn.chatgpt.com/docs/agent-approvals-security).
User configuration does not prove the active session grant changes. Keep filesystem limits,
use only the approved VM destination, and verify actual access plus the guest host key
before authenticating as Standard user StudioTest. Do not export passwords/private keys.

Fixture installers live in
`.runtime/p0-05-install-upgrade-fixture/artifacts/`. Version **0.1.1 is a packaging-only
upgrade fixture**, not a new production release. Its existing frontend/backend are reused;
the original checkout/version/artifacts stay unchanged. Verify both installer SHA256 values
against `build-result.json` before transfer and after copying into the guest.

| Check | Required evidence |
| --- | --- |
| Clean standard-user installation of 0.1.0 | New guest profile has no Studio configuration/history; installer launches without elevation and installed payload hashes/version are recorded. |
| Real working system | Chat generates a real local response; deny a file-creation request, then approve a fresh request in a disposable project and verify exact file bytes. No separate backend terminal. |
| Seed retained state | Create a harmless conversation, text attachment and changed preference; save their IDs/content hashes and configuration before upgrade with Studio closed. Use only fixture content. |
| Actual version upgrade | Install 0.1.1 over 0.1.0 in that guest account; verify the installed version/payload changes. A same-version reinstall does not count. |
| Configuration/history retention | Existing configuration, conversation/message identities, fixture contents, attachment and preference survive; reopen and generate another reply. Compare logical records rather than requiring SQLite page bytes to stay identical. |
| Default uninstall | Close Studio, uninstall without selecting data deletion, verify program removal and retained guest configuration/history. Reinstall and check the retained fixture. |
| Explicit data-delete uninstall | In this disposable guest only, select delete application data; verify intended guest app state is removed while unrelated guest canary/project files remain. Record actual scope. |
| Owned cleanup | Close Studio and observe its owned backend/workers exit. Independently running services remain untouched. |

Record each check as passed, failed, blocked or untested with versions, hashes and actual
observations. Preserve failures. Do not export guest credentials, private screenshots or
full production databases. The retained matrix now passes; a fixture build alone did not
establish that result. Initial helper dependency/selector/syntax/download-observation failures
are preserved separately from final actual native observations.54 relevant regression tests
pass,1 opt-in diagnostic is skipped, Ruff passes. Restore/checkpoint cleanup must affect only
the explicitly named test VM after required evidence has been retained. This release-test
environment is not P1-07's still-missing isolated agent execution backend.
