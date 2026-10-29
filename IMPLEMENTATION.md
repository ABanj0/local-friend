# Implementation Progress

## Publication scope clarification (2026-10-28)

Publication status (2026-10-28): an opt-in Hyper-V command backend is now present in
source, with input staging, ownership leases and fail-closed dispatch. Its live isolation,
canary/network/cancellation and restart acceptance remains incomplete; P1-07 stays open.
See [execution backend scope](docs/execution-backends.md). Earlier statements that no
backend exists or host provider access is denied describe the dated stages below.

## P1-07 resumed: provider restored; separate sealed execution VM prepared (2026-10-28)

Actual resumed token has Hyper-V Administrators membership/role, without a full
Administrator token; named Get-VM succeeds. Earlier provider-denied gate is superseded.
Inspect the existing VM/configuration/disks/checkpoints/services and available storage.
Use official data-consistent Export-VM and extended stateful ACL documentation. Export
the dedicated release-test VM without stopping/resetting it, then import a separate copy
with a generated new identity under .runtime/p1-07-execution-vm. Original remains running.
Remove the copy's DVD, disable its automatic checkpoints/start, and set bounded memory/CPU.
Apply IPv4/IPv6 deny-all network rules before first boot, with host-initiated SSH and only
temporary DHCP.4GB startup fails for memory availability;2GB startup/4GB maximum succeeds,
and actual memory status is OK. Do not stop unrelated models or the original VM to force it.

Pinned-key SSH into the new VM proves StudioTest/Standard user. The expected SSH host key
comes from the already verified, data-consistent template; no unknown key is auto-trusted.
Remove only the bootstrap DHCP rules. Actual remaining rules are inbound/outbound ANY deny
plus stateful inbound TCP22 from the host gateway. SSH still works; guest probes of public
TCP443 and host SMB fail. These preliminary probes do not alone prove the full isolation
contract. No untrusted project execution or application backend change has occurred yet.

Implementation/acceptance checklist (P1-07 remains open):

- [x] Verify actual provider, separate owned VM identity and pre-boot network policy.
- [x] Verify Standard-user SSH with the trusted template key; remove DHCP after bootstrap.
- [ ] Record a clean owned baseline/checkpoint and validate reset/boot/network sealing.
- [ ] Add the execution-backend interface and explicit trusted-host/VM labels.
- [ ] Integrate approved bounded input staging and synchronous Python/test execution.
- [ ] Keep unsupported isolated operations/configuration fail-closed; no host fallback.
- [ ] Implement durable VM ownership/lease, cancel/parent cleanup and stale-owner recovery.
- [ ] Verify real host file/environment canaries, denied-network positive/negative controls,
      only reviewed transfer, test counts, zero/skipped/failure handling and cancellation.
- [ ] Run relevant source/API/UI/CLI/regression/build/frozen checks; record exact limits.

Evidence: .runtime/p1-07-readiness/access-restored.json, first-clone-ssh.json,
sealed-network-probes.json; .runtime/p1-07-vm-template-20261028/export-result.json and
.runtime/p1-07-execution-vm/ownership.json, before-boot-policy.json, sealed-policy.json.
Private VM image/account data and SSH private keys remain local ignored runtime material;
do not include them in public archives or diagnostic exports. Previous blocked-audit notes
remain historical. Scope is coding/test execution; host desktop/browser remain separate.

## Post-P0-05 continuation blocked after repeated prerequisite checks (2026-10-28)

The same remaining condition recurs across the completed native-matrix turn, following
permission-clarification goal turn and this continuation. Actual local group membership
and token both exclude Hyper-V Administrators; Administrator token is also false. The
named Get-VM query still receives VirtualizationException/permission denial. Guest SSH
last succeeds as Standard-user StudioTest; do not describe this as lost guest access.

Read current requirements, source host Coding/run_process path, specialist gate/tests and
saved actual-model outcomes again. No execution backend exists; VM lifecycle/network/input/
output isolation remains unimplemented.4B routing quality and both specialist benefit
gates remain failed; optimization's per-case nonregression is false. Optional parser work
has neither selected demand nor its isolation prerequisite. No safe independently eligible
increment or confirmed live background job is found. No failed gate is bypassed or repeated
to obtain a pass. Evidence: .runtime/roadmap-gates/20261028-after-p005/blocked-audit-3.json.

Set goal blocked, not complete, pending owner-directed host authorization/setup or another
genuine prerequisite change. The optional membership procedure and narrower owner-run
command alternative are in docs/windows-test-vm.md; the agent makes no privilege change.
After owner action, verify actual provider access before implementing P1-07. No application
change/test rerun or completion-checkbox change is justified by this audit. P0-05 stays
accepted at its verified scope; all remaining roadmap requirements retain their open state.

## Post-release access distinction and owner-directed remedy (2026-10-28)

Recheck after the P0-05 completion: pinned key-only SSH still returns StudioTest with a
Standard-user token. Host Get-VM still returns VirtualizationException/permission denial.
Independent token inspection shows EXAMPLE-PC\ExampleUser has neither an active Administrator nor
Hyper-V Administrators role. Read-only local SAM queries confirm the enabled ExampleUser account
and Hyper-V Administrators SID S-1-5-32-578. This is host management authorization, not loss
of guest SSH. No account/group/daemon/firewall change is made.

Owner asks how to grant access or perform commands themselves. Verify Microsoft's
Hyper-V/LocalAccounts documentation and add an optional host-only, owner-executed group
membership procedure in docs/windows-test-vm.md, including its all-local-VM scope, full
sign-out/token refresh and actual provider recheck. Specific reviewed administrator-run
commands remain an alternative; do not elevate the entire agent. Actual membership/access
remains ungranted/unverified pending the owner's choice/action. P1-07 is still unchecked;
neither SSH transport nor prospective membership establishes isolation. Review remaining
source/gates: specialist and routing retain failed measured benefit/quality results, parser
ingestion lacks selected demand/isolation, and optimization has its retained non-regression
failure. No independent eligible increment or background work is found. No unchanged
application tests are rerun and no full roadmap completion is claimed.

## P0-05 third increment: real Standard-user VM matrix passed (2026-10-28)

Complete the installed-product gate in Studio-Release-Test as StudioTest, not the host
production account. The owner's clean-profile/initial0.1.0 installation observations are
followed by independent key-only SSH token/payload/model/artifact readback. An isolated
CPython3.12.14 and pinned Playwright test toolchain are hash-checked and installed only in
the new guest fixture. Temporary scheduled tasks run with the existing interactive token,
RunLevel0, without passwords or administrator membership. No application source change,
global Python install, host production state change or approval-policy change is needed.

Actual installed Tauri/WebView2 testing uses its real IPC/backend and Ollama0.40.12/9B;
there is no browser bridge or model fixture. Verify the real Windows Open dialog and file
selection, bound text attachment, VM-ATTACHMENT-63182 reply, actual guest clipboard,
184-byte downloaded Markdown,1024x768 screenshot preview, temperature0.3 persistence and
Stop's durable cancelled outcome. Independently compare the export's exact bytes with the
stored two-message transcript; attachment body is excluded. Earlier denied/approved
creation records independently show denied/no verifier versus observed/one passed artifact
verifier, matching the14-byte VM-APPROVAL-OK file. Cancel creates no test verifier.

Close the exact guest native window normally before capturing read-only SQLite logical
hashes and a guest-only backup; never instantiate Store or run migrations for observation.
Execute the retained, hash-verified0.1.1 packaging fixture over0.1.0 as Standard user.
Installer exits0; installed version changes0.1.0→0.1.1 and native SHA256 changes from
902be457a388607067d3e28350ddb25095c5398bd07116fdb86d1a850ccedcf4 to
bd4e312913bd08f72d915e8aad469cb1f422d527fc6ff95ab3534a9889f7fec6.
Backend SHA256 stays95ca89a8c363a940f1c58fc9f5a7b68844d4b7caf6a02a187761fe57cfcda44b.
All146 original logical records, configuration hash, attachment binding/content and changed
preference are identical. Reopen the actual retained attachment/settings and generate
VM-UPGRADE-OK. This is an actual version upgrade, not a same-version reinstall.

Exercise the actual NSIS uninstall dialog with its delete-data checkbox initially unchecked.
Default uninstall removes program payload while preserving all162 current logical records,
configuration and workspace artifact. Reinstall the same0.1.1 package: exact installed native
hash and all162 records match; the real app reopens retained state and returns VM-REINSTALL-OK.
Close normally, then explicitly select the real delete-data checkbox in this disposable
guest. Both LocalAppData and a seeded Roaming AppData Studio directory are removed, including
the default workspace inside app data. The separate canary project, attachment source and
independent Ollama PID10604/creation identity/health survive every installer phase.

Final independent observation: no Studio/backend/fixture helper, debug/backend listener or
fixture scheduled task remains. Guest program and Studio data are absent as intended by the
explicit delete test. Guest-only raw backups and benign evidence remain outside app data;
no raw database/config/screenshot/private key is exported. Host installation/history are
untouched.0.1.1 remains a packaging-only test artifact, not a published update.

Verification:11 required phase/readback reports plus7 completed native-control checks;
55 relevant regression tests discovered,54 passed,1 opt-in native diagnostic skipped in
9.289s, zero failures/errors. Ruff passes. Unchanged application binaries/frontend are not
rebuilt or claimed newly covered by a full default suite. Preserve earlier helper failures:
missing win32ui dependency (use scoped Win32 controls instead), dialog-ID/accessible-name
assumptions, one generated helper syntax error, CDP's download override (restore default
before native export), and TIME_WAIT mistaken for a listener. Actual final observations
verify the corrected checks; those earlier attempts are not relabelled as passes.

Evidence: .runtime/p0-05-vm-acceptance/validation.json and its referenced phase reports,
native_continue-result.json (completed checks only), native_remainder-result.json,
verify_export-result.json and cleanup-observe-result.json. P0-05 third now closes using
these and the already accepted lifecycle/packaging/native subchecks. Update README, desktop
and VM guidance plus architecture/gap status. No unrelated source changes are committed.

Next: P1-07's explicitly configured disposable execution backend. A fresh host Get-VM on
the named VM still returns permission denial. The release-test guest/SSH transport supplies
neither a managed disposable execution boundary nor enforced denied networks; do not run
untrusted agent code in it or label host Job Objects as isolation. That increment remains
blocked on supported administrator-backed VM control and a suitably isolated execution
image/network. Existing review/routing/optimization benefit gates remain failed, not retried.

## Verified key-only SSH as guest Standard user; installed evidence collected (2026-10-28)

Owner's hexadecimal host fingerprint exactly matches the scanned ED25519 public key:
[private guest host-key digest omitted]. Pin the verified
candidate in isolated known_hosts; keep StrictHostKeyChecking and key-only BatchMode.
Initial login fails locally because the original private key belongs to the former sandbox
execution identity and the current Windows identity cannot read it. Do not broaden its
ACL or request elevation; generate a new temporary key under the current user and verify
its readability before enrollment. Existing global SSH settings remain untouched.

Current permissions also restore VMConnect/UIA access. Observe only the named VM window,
verify its foreground handle before input, and find the guest's normal PowerShell terminal.
Actual whoami is EXAMPLE-GUEST\StudioTest. The console shows previous multiline paste/parser
failures. Initial virtual-key injection loses case; a small Unicode encoded-command probe
successfully prints its exact case marker. Send the guarded public-key update with that
method, preserving existing keys. Keyboard-input process7059 completes; a later guarded
Unicode input finishes, and actual key-only SSH returns exit0 with user=studiotest,
computer=ExampleUser, standard_user=true. Host clipboard is restored after the unsuccessful
menu-paste attempt; no clipboard content/private key is logged or exported. An initial
occluded-window capture is removed; retained console observations are from the confirmed
foreground VM. No host browser/app input is sent.

Actual read-only guest evidence now proves the installed0.1.0 main EXE is9,519,104 bytes,
SHA256902be457a388607067d3e28350ddb25095c5398bd07116fdb86d1a850ccedcf4; backend is
72,566,540 bytes, SHA25695ca89a8c363a940f1c58fc9f5a7b68844d4b7caf6a02a187761fe57cfcda44b.
Both match the retained package expectations. Guest localhost Ollama reports0.40.12 and
qwen3.5:9b digest56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90.
The approved test artifact actually exists with VM-APPROVAL-OK,14 bytes and SHA256
58cd795166a6278f683c3f93eae2e0eb0053f59f3430aa311b7ff115e4805b06. These supersede
earlier uncollected guest hash/model assertions; no GPU or complete native release claim.

Revoke only the exact obsolete test public-key line. First File.Replace call with a null
backup fails under Windows PowerShell binding before publication; original keys are
preserved and staging is cleaned. Correct with a unique backup path, exact preimage check,
atomic replace/readback and owned backup cleanup. Old key removed, current key retained;
a fresh key-only connection again returns EXAMPLE-GUEST\StudioTest. No password, account promotion,
daemon configuration, additional firewall rule or unrelated credential is changed.

Verified scope: transport, guest host identity, public-key authentication, Standard-user
execution, actual installed payload/model/artifact readback. Remaining: exact denial/journal
records, attachment/preference baseline, native controls, actual0.1.1 upgrade/retention and
uninstall/data checks. P0-05 third/P1-07 stay open; SSH transport is not an implemented
agent isolation backend. No unchanged application regression suite is rerun for this
operator work. Evidence: .runtime/p0-05-vm-ssh/bootstrap-auth-observations.json,
guest-readonly-evidence.json, obsolete-key-revocation*.json and post-revocation-login.json.
Private key files must never be included in an archive/export.

## Guest host fingerprint has two ambiguous-character differences (2026-10-28)

Owner supplies the console ED25519 SHA256 fingerprint. Exact comparison with the scanned
VM key differs at Base64 positions6 and41: reported uppercase I versus scanned lowercase l
and digit1. This is plausibly transcription ambiguity, not evidence of an authenticated
identity. Do not fuzzy-match, auto-trust the scanned key or attempt key authentication yet.
Retain .runtime/p0-05-vm-ssh/fingerprint-comparison.json. Request a SHA256 hexadecimal
rendering of the same public host key from the guest console to remove I/l/1 ambiguity;
no private key, password, ACL change or re-enrollment is needed. No release/test pass.

## Guest key enrollment reports Permission denied (2026-10-28; unresolved location)

Owner reports only "Permission denied" after the enrollment/fingerprint block. The exact
failing line is not supplied; do not assume the authorized_keys write failed or succeeded.
Actual managed transport still reaches strict unknown-host-key refusal, so no key login
can be tested before identity verification. No host key is trusted automatically.

The last command reads a public host-key file under ProgramData; request that single
fingerprint read from guest Administrator PowerShell to distinguish its access restriction
without changing ACLs or rerunning account-key creation as administrator. Obtain the full
error if the read fails. Keep StudioTest Standard and preserve any already-created
authorized_keys file. No password/private key request, configuration change, service
restart, broad permission grant or authentication success is claimed.

## Permission change restores managed SSH transport (2026-10-28)

Owner changes the execution permission environment and requests verification. Actual direct
TCP22 now succeeds and returns SSH-2.0-OpenSSH_for_Windows_9.5. Actual ssh.exe reaches
strict host-key checking and refuses the unknown ED25519 host key, replacing the earlier
socket Permission denied. Networking is verified restored; authentication is not.
Evidence: .runtime/p0-05-vm-ssh/permissions-recheck-20261028T205636Z.json.

Retrieve only the identified VM's public ED25519 host key using ssh-keyscan; retain it as
an unverified candidate, not a trusted known_hosts entry. Fingerprint candidate is
[private guest host-key fingerprint omitted]. Out-of-band guest-console comparison
is required before trusting it. Prepare one-time Standard-user enrollment of the existing
temporary client public key with restrict options, preserving any existing authorized_keys
through exclusive CreateNew. Account and administrator-group guards prevent applying it
on the host or as the guest administrator. It prints the guest host public-key fingerprint;
no password/private key is requested or exported and no sshd setting changes.

Operator syntax and actual wrong-host-account refusal pass; no host key file is written.
Guest execution remains pending. New broader execution permissions are used only for this
authorized VM workflow; no unrelated files/processes or security controls are changed.
Next: owner runs the enrollment block in normal VM PowerShell as StudioTest and supplies
the actual host-key fingerprint. Then compare/pin and test key-only authentication before
automating guest checks. No release acceptance or SSH login is claimed yet. Evidence:
.runtime/p0-05-vm-ssh/candidate-host-key.json and enrollment-readiness.json.

## Host-to-guest SSH TCP succeeds; managed session remains denied (2026-10-28)

After the targeted existing-rule profile instructions, owner supplies actual normal-host
Test-NetConnection:192.0.2.2:22, source192.0.2.1/Default Switch,
TcpTestSucceeded=True. The active guest NetworkCategory itself was not supplied; record
the successful external TCP test without inventing that field or an authenticated login.
Actual managed ssh.exe retry still exits255 with connection Permission denied before
host-key exchange/authentication. Evidence: .runtime/p0-05-vm-ssh/after-profile-fix.json.
No further guest firewall changes are justified by this difference.

Apply the openai-docs skill for current execution-permission guidance. Inspect only local
Codex config's sandbox/network-related fields, not credentials: no explicit user-level
network/sandbox selection is present there. Official OpenAI Windows sandbox and permission
documentation confirms command/child network enforcement is separate from filesystem and
approval policies. Current session instructions explicitly restrict networking and reject
sandbox escalation requests; do not attempt a proxy/tunnel, broad security disabling or
configuration write outside the workspace to bypass that grant.

Official docs support workspace-scoped filesystem permissions with approved command
network access and exact local-IP allow rules when the managed proxy is enabled. They do
not prove this installed client offers the same menu/configuration selection or that raw
SSH will use a permitted proxy automatically. Need owner-visible permission/profile options
or an administrator-approved execution-policy change for the intended guest connection.
No global/user Codex configuration, guest key file, host known_hosts or SSH daemon setting
is changed. Temporary client key remains local/ignored; no password is requested. Once
transport is actually available, verify the guest host key and arrange key-only StudioTest
authentication before commands. GUI acceptance remains separately scoped.

## Guest SSH rule is Private-only (2026-10-28; owner diagnostic values)

Owner supplies actual listener0.0.0.0:22 and active rule: Enabled=True, Inbound, Allow,
Profile=Private, LocalAddress=Any, RemoteAddress=192.0.2.1, Protocol=TCP, LocalPort=22.
This verifies the reported listener is not loopback-only and identifies a possible rule/
network-category mismatch. Guest active NetworkCategory has not been supplied; do not
state the cause as proved or the connection as fixed. No authentication has succeeded.

Next inspect guest Get-NetConnectionProfile, then let this one existing SSH rule apply to
the required network profiles while retaining the exact host-only remote address. This
is explicitly scoped SSH setup requested by the owner; it does not alter firewall global
enablement, other rules or Studio's localhost binding. Re-test from normal host afterward,
then actual managed SSH if host TCP succeeds. No remote/key authentication, primary release
acceptance or source/test change is claimed. Microsoft Set-NetFirewallRule documentation
and installed parameter metadata confirm Profile/RemoteAddress support.

## Normal-host SSH retest still fails after guest loopback confirmation (2026-10-28)

Owner supplies another actual host Test-NetConnection: same guest192.0.2.2:22,
Default Switch/source192.0.2.1, TCP=False and ping timeout. Fresh ARP still maps the
same guest MAC. Guest service/loopback readiness was owner-confirmed; external traffic
remains unsuccessful. Do not replace this failure with a localhost pass or attribute it
solely to the managed execution environment. No authentication is reached.

Request read-only guest listener binding and active firewall rule/action/profile/address/
port observations per Microsoft's troubleshooting guidance. Preserve the existing trusted
host scope; no broad allow rule, firewall disable, account promotion or credential request.
No source changes/test pass/roadmap completion. Actual outputs are needed before a targeted
fix. No repeated managed SSH probe is warranted for the same unchanged denial.

## Guest SSH loopback succeeds; external route still unverified (2026-10-28)

Owner explicitly confirms all three diagnostic expectations: OpenSSH capability Installed,
sshd Running, guest loopback TCP22=True. Treat these as owner-observed service/listener
readiness, not successful host-to-guest access. Retrying actual ssh.exe from this managed
session still exits255 with connection Permission denied before host-key exchange or
authentication. No credentials/configuration/rules changed by the agent. Evidence:
.runtime/p0-05-vm-ssh/after-guest-listener.json.

Next isolate remaining conditions: guest listener binding and the active inbound rule's
enabled/profile/action/address/port values; also repeat the owner's normal-host TCP test
after this confirmed running state. Preserve the host-only192.0.2.1 scope and existing
firewall policy. Do not assume a service restart, broad allow rule or password would fix
an unobserved transport problem. Studio's pending native upgrade tests remain separate.

## Normal host also cannot reach guest SSH (2026-10-28; owner output)

Owner supplies actual Test-NetConnection output:192.0.2.2:22, source192.0.2.1,
Default Switch interface, TcpTestSucceeded=False (PingSucceeded=False). Fresh ARP still
matches that address to the known VM MAC. This broadens diagnosis: managed10013 alone
does not explain the owner's normal-host TCP failure, and guest SSH installation/listening/
firewall readiness is still unverified. Ping failure alone does not locate the TCP issue.
No password/key authentication has been reached and no additional rule is opened.

Use Microsoft's OpenSSH port22 troubleshooting sequence: inspect the guest capability state,
sshd service and guest loopback TCP22 first. Obtain those actual outputs before changing
settings; if loopback works, inspect the scoped inbound rule and host-to-guest path next.
No host or guest configuration mutation/test pass is claimed. Owner one-time administrator
setup remains a separate operation from the required Standard-user Studio acceptance.

## SSH automation investigation: current transport denied (2026-10-28)

Owner asks to automate guest testing over SSH. Inspect host SSH tools and Microsoft's
Windows OpenSSH setup/configuration docs: supported guest server installation requires
one-time administrator setup; a key-only Standard-user connection can then run commands,
but SSH alone is not evidence of native interactive UI operation. Managed Hyper-V network
enumeration remains denied. Read host ipconfig/ARP only; match the previously supplied
guest MAC00-15-5d-00-00-01 to192.0.2.2 on host Default Switch192.0.2.1. Owner
independently confirms that same IPv4/default gateway pair.

Prepare a dedicated temporary Ed25519 client key in gitignored .runtime/p0-05-vm-ssh
(private key never printed/exported), with key-only BatchMode, no agent/forwarding/proxy,
strict known-host verification and isolated configuration/known-host paths. ssh -G validates
client options; ssh-keygen verifies the private/public pairing. Existing credentials and
host SSH configuration are untouched. This is local preparation, not a successful login.

Actually probe only the identified guest's TCP22: Python gets immediate PermissionError,
Windows10013. The actual Windows ssh.exe also exits255: "connect to host192.0.2.2
port22: Permission denied". Both failures occur before authentication/host-key exchange;
do not describe this as a wrong password, installed guest server or reachable SSH endpoint.
Guest OpenSSH readiness remains unknown. No guest server/configuration/firewall change,
port forwarding, security-control relaxation or substitute proxy is attempted. Enabling
the guest server alone is not proven sufficient to resolve current host execution access.

Owner address information is now sufficient; no further ipconfig request is needed. The
transport boundary needs an approved environment/access change before SSH can automate
the command-line parts. Preserve existing owner-observed GUI/artifact results and continue
the pending attachment/upgrade acceptance in the VM until such access exists. No feature
or release acceptance closes. Evidence: .runtime/p0-05-vm-ssh/readiness.json,
transport-probe.json, ssh-probe.json and ssh-probe.log; no new dependency or test repeat.

## Guest approved-artifact readback confirmation (2026-10-28; owner-observed)

Following the fresh-approval/external PowerShell byte-read instructions, owner answers
"That is the output." Treat this as confirmation of the stated VM-APPROVAL-OK text and
14-byte expectation, not a pasted SHA256/journal result. The independently computed
expected hash is58cd795166a6278f683c3f93eae2e0eb0053f59f3430aa311b7ff115e4805b06;
do not label it as observed from the guest. Denied-task exact result and actual verifier/
approval records also remain uncollected. No broad release checkbox closes from this
bounded owner confirmation. Next: harmless text-attachment conversation and changed
preference as actual retained-state fixtures before the0.1.1 upgrade; preserve earlier
Chat/Agent history and the artifact. No application change or repeated unit suite.

## Guest denied-write absence reported (2026-10-28; owner-observed)

After the Agent/Coding deny-first instructions for vm-approval-check/hello.txt, owner reports
the independent guest PowerShell Test-Path returns False. This establishes owner-observed
absence at that scoped path; the exact task denial message/journal has not been supplied.
Do not invent a durable approval record from file absence alone. Next: fresh submission
of the same fixed14-byte/no-newline request, fresh approval of that exact destination,
then guest byte/text/SHA256 readback. No installed tool success, upgrade or full release
acceptance is inferred yet. No source change or test rerun.

## Guest installed Chat produces the fixed marker (2026-10-28; owner-observed)

Owner reports actual installed Studio Chat reply `VM-CHAT-OK` after selecting the local9B
model and submitting the fixed marker request. This closes the narrow owner-observed real
Chat generation check following native connection; it does not independently establish
guest model digest, GPU acceleration, tool effects or full release acceptance. No host
inference or source/test change. Next: Agent mode, deny a harmless scoped file-creation
proposal, confirm no file, then a fresh submission/fresh approval and exact byte readback.
Keep all workflow/upgrade/history/uninstall acceptance outstanding until observed.

## Guest installed Studio connects locally (2026-10-28; owner-observed)

After confirming the clean Standard-user precheck and receiving the hash-guarded0.1.0
installer launch instructions, owner reports "It connected." Record installed Studio's
local connection under that guest workflow as owner-observed. Exact guest installed payload
hash/version and actual generated reply/tool effects are not independently inspected.
No administrator prompt is reported. Do not equate connection to model inference or close
P0-05 third. Next: Chat using the configured local9B model with a fixed harmless marker,
then denied/freshly approved Agent file creation with independent guest file readback.
Seed harmless history/attachment/preference evidence only after these core checks pass,
then execute the actual0.1.1 upgrade and uninstall/data matrix. No application changes or
test rerun; managed VM access remains the prior external inspection boundary.

## Guest pre-install account/clean-profile values match (2026-10-28; owner-observed)

After explicitly distinguishing the expected explanatory text from the actual JSON, the
owner confirms "matches": StudioTest=true, StandardUser=true, StudioDataExists=false,
StudioInstalled=false. Record this as owner-observed guest precondition evidence; managed
guest inspection is still unavailable. It does not prove model inference or installation.
The exact CD drive letter remains unspecified; identify the sole STUDIO_TEST optical volume
inside guest PowerShell, verify setup010.exe against the retained SHA256 before launching
it normally. Include a StudioTest-account guard to catch accidental execution on the host.
Require actual installer/startup observations next. No guest install or primary release
acceptance is marked complete and no unchanged application suite is repeated.

## Guest pre-install account observation requested (2026-10-28)

Owner acknowledges the transfer-disc instructions without a drive letter or command
output. Do not infer a successful checkpoint, exact attachment or installer run. Provide
the same read-only account/Studio-footprint observation as inline guest PowerShell, with
an explicit nonempty-group guard, so no script execution-policy change is needed. Await
the actual booleans before treating the Standard user/clean profile precondition as met.
No application or transfer-image change, test rerun or acceptance closure.

## Prepared guest installer handoff (2026-10-28)

Owner replies "Correct" after the model-pull/list instructions. No exact listing, digest
or inference output is supplied; do not promote that acknowledgement to independently
verified guest model/inference acceptance. Proceed with reversible media handoff while
those checks remain part of the actual installed workflow. Fresh Get-VM remains Access
denied; the agent cannot attach the DVD itself. Rehash the prepared image: its SHA256 still
matches f1842456b3bdd29ef2b4f1dd2a75165d07b0786e1acb584368cc3b106563ceb5.

Next owner actions are a pre-install checkpoint and attaching that specific data ISO to
the existing test VM's DVD through normal host Hyper-V Manager. Then inspect the guest
account/empty Studio footprint before running the0.1.0 installer. No actual checkpoint,
attachment, guest observation, installation, test rerun or acceptance completion is claimed.

## Guest Ollama version reported; no local models yet (2026-10-28)

Owner reports guest `ollama --version` is0.40.12 and `ollama list` is empty. This confirms
owner-observed CLI installation/version, not model availability, inference or Studio
acceptance. It differs from the host's previously measured0.40.7; do not infer identical
compatibility or performance. Next: run the already documented `ollama pull qwen3.5:9b`
inside the VM, retain its actual success/error and verify the guest model listing. No
host-service request, new download by this agent, test repeat or acceptance closure.
The prepared installer data disc remains the next handoff after guest model readiness.

## Post-transfer prerequisite audit (2026-10-28; first unchanged check)

The prior turn made progress by producing and independently verifying the scoped transfer
disc. Fresh Get-VM still returns Access denied. No guest Ollama version/model output or
media-attachment result has arrived, and no live tool/test handle exists. Download report
is not installation/inference evidence. Review/routing/optimization candidates retain
their failed gates; no independent remaining increment is actionable. This check makes
no progress, reruns no tests and closes no acceptance. Goal stays active on the first
unchanged audit. Next: documented guest version/pull/list output, then controlled media
attachment/clean install. Evidence:
.runtime/roadmap-gates/20261028-after-transfer/audit-1.json.

Second unchanged post-transfer check: actual Get-VM still returns Access denied; guest
runtime/model output and disc attachment remain unobserved. No live test handle or newly
qualified independent increment exists. No progress, test repeat or acceptance change;
goal remains active at this second check. Evidence:
.runtime/roadmap-gates/20261028-after-transfer/audit-2.json.

Third consecutive unchanged check: actual VM provider remains Access denied; guest Ollama
version/model and transfer attachment are unobserved. Prepared media remains present;
there is no live test handle or new independent qualified increment. Continuous execution
is blocked, not complete, pending owner guest results/normal-session VM operations. No
test repeat, privilege bypass or acceptance closure. Evidence:
.runtime/roadmap-gates/20261028-after-transfer/audit-3.json. Resume with guest version/list
after the local9B pull; then attach the prepared disc for the documented release matrix.

## Guest Ollama download reported; verified installer transfer disc prepared (2026-10-28)

Owner reactivates continuous roadmap execution and reports Ollama downloaded in the VM.
Distinguish download from installation and model availability: those remain unverified.
Inspect AGENTS, current pending release contracts, setup guidance, installed runtime
discovery and fixture artifacts. Managed VM provider still returns Access denied. The
previous reopening explanation was no implementation progress; this turn prepares an
actual independently checked release-test handoff while guest operations require owner
interaction. No host feature/security changes or unrelated model/provider retries.

Windows IMAPI2FS is available. Using Microsoft's IFileSystemImage/CreateResultImage API,
build a credential-free nonbootable ISO9660/Joliet data disc without installing dependencies.
An explicit five-file allowlist includes exact renamed0.1.0/0.1.1 installers, their SHA256
manifest, test-order instructions and a read-only guest account/Studio-footprint observer.
No autorun, models, host configuration, history or tokens. Existing source installers are
hashed before staging and untouched; output creation refuses an existing image. The observer
reports booleans only and tests administrator-group membership, not merely elevation, to
avoid treating an unelevated administrator as the required Standard user. It does not
install anything or assert release acceptance from its exit code.

Actual verification: tar lists exactly the five allowed files; each is read back from the
ISO and its bytes/SHA256 match staging. Both embedded installer hashes match the original
build-result manifest. PowerShell observer parse has zero errors. ISO is148,260,864 bytes,
SHA256 f1842456b3bdd29ef2b4f1dd2a75165d07b0786e1acb584368cc3b106563ceb5. No unit or full
regression repeat is warranted for this artifact/documentation-only preparation; actual
artifact verification is not guest installation testing. Source operators, payload manifest
and validation are retained under .runtime/p0-05-vm-transfer/.

Document normal guest Ollama version/local9B pull/list checks, exact host admin DVD handoff
with a single-drive guard, and guest account/empty-profile observations before0.1.0 install.
Verify local Set-VMDvdDrive metadata accepts the DVD object pipeline. No DVD was attached,
no guest setup executed, no new download or host inference invoked, and no release checkbox
closes. Next owner action: finish the downloaded Ollama installer in StudioTest and retain
the guest version/pull/list output. Then checkpoint, attach prepared media and execute the
standard-user clean install/real workflows/upgrade/data matrix. Evidence:
.runtime/p0-05-vm-transfer/validation.json; official references are in the VM guide.

## Guest reaches desktop and test-account sign-in (2026-10-28; owner observations)

Owner confirms the Studio-Release-Test on localhost Virtual Machine Connection window,
Windows desktop in Basic session, and completion of the StudioTest sign-out/sign-in step.
Guest setup/boot is now owner-observed; do not keep reporting the earlier DVD failure as
the current blocker. Actual group membership, guest runtime and installer acceptance still
need verification. Managed Get-VM remains Access denied, so no direct guest inspection,
copy operation or install has been performed by this agent.

Inspect release template, actual Ollama discovery code, desktop runtime guidance and both
fixture artifacts. Rehash both installers:0.1.0/0.1.1 match their existing expected sizes
and SHA256 values. Official Ollama Windows documentation confirms per-user installation
without administrator rights. Clarify the guest guide: packaged Studio does not require
Node/Rust/development setup, Ollama runtime and model are separate steps, and external
Python is needed only for Python execution workflows. Preserve localhost service scope
and the existing host installation. No application source changes or repeated tests.

Next owner action: install Ollama normally inside the VM while signed into StudioTest.
Then prepare model/controlled installer transfer and the clean-install/upgrade matrix.
No guest inference, GPU, standard-user group membership, Studio installation or release
completion is claimed. Evidence: .runtime/p0-05-vm-guest/readiness.json.

## VM DVD boot failure: preserve VM and remove initial-console timing hazard (2026-10-28)

Owner reports DVD boot-loader failure, no network image and no OS on disk. Fresh filesystem
inspection shows the created VM directory, system.vhdx and its checkpoint disk. Get-VM
still returns Access denied, so actual DVD attachment, firmware settings and keypress
timing cannot be independently inspected. Do not infer the ISO is corrupt or disable Secure
Boot. Read-only tar inspection sees only the ISO bridge's UDF README; that reader does not
establish absence of UEFI files. Preserve the image, VM and disks without alteration.

Source confirms initial setup starts the VM before opening its console. A missed brief
DVD keypress is a plausible cause, not a verified diagnosis. Microsoft's boot instructions
require the keypress; a Microsoft-hosted Hyper-V discussion describes this console timing.
Remove automatic Start-VM from the creation script: new VMs stay off while the console
opens, with clear Start/click/Space instructions. Update the success safety contract to
require zero start calls and document recovery using the existing VM's Restart, followed
by read-only normal-session DVD/firmware inspection if the retry fails. No existing VM
setting, security feature or disk is changed; do not rerun creation over it.

Final verification:11 passed,0 skipped in2.300s (eight replaced-Hyper-V safety contracts
plus three discovery checks); full local_agent/tests Ruff and PowerShell syntax pass.
No real Windows Setup boot is verified and no roadmap acceptance closes. Next owner
action is Restart in the current VM console and immediately respond to the DVD keypress.
If unsuccessful, retain Get-VMDvdDrive/Get-VMFirmware output for diagnosis. Evidence:
.runtime/p0-05-vm-boot/media-observation.json, validation.json and unit/lint/syntax.log.

## Windows ISO supplied; VM creation operator ready (2026-10-28)

Owner asks to complete VM setup after moving the ISO. Inspect current instructions and
actual filesystem/provider state. The supplied image is Windows11.iso.iso in the intended
directory,9,047,330,816 bytes. Rename that exact file to Windows11.iso after confirming the
destination is absent; no image bytes changed. Publisher digest/authenticity is not verified.
New-VM/Get-VM are installed, but actual Get-VM/Get-VMSwitch still return Access denied.
The intended VM directory is absent; VM inventory remains unknown rather than empty.

Add scripts/new-windows-test-vm.ps1 and replace the guide's multiline creation block with
one command. The script checks media, existing folder/VM, provider access and existing
Default Switch before mutation; it creates only the fixed new VM/disk. Subsequent settings
target the returned VM object: Gen2,16GB static RAM,4 vCPU,128GB dynamic disk, Secure Boot,
vTPM, installer DVD/first boot, start and interactive VM console. It never elevates itself,
changes ACLs/features/networks, deletes partial resources or attaches to an existing VM.
Partial failure stops and asks the owner to preserve the VM/disk. This is release-test
setup support, not P1-07 isolation or verified guest installation.

Verify parameter availability against installed Hyper-V command metadata and Microsoft's
New-VM/Set-VMFirmware/Enable-VMTPM documentation. Eight PowerShell-driven safety contracts
use replaced Hyper-V calls: missing ISO/provider/switch, existing VM/directory, partial
failure, ambiguous DVD and success object targeting/resources/console. Initial harness
scope error causes three failures; fix only the test call collector's subprocess-local
scope. Final eight contracts plus three discovery checks pass:11 passed,0 skipped,2.360s.
Full local_agent/tests Ruff and PowerShell parse pass. Actual script invocation exits1
with provider Access denied before folder creation, as independently checked afterward.
This is a genuine managed-session permission boundary; no elevated bypass is attempted.

No VM was created, no Windows installer was launched, no release checkbox closes. Next:
owner runs .\scripts\new-windows-test-vm.ps1 in normal Administrator PowerShell, then
completes Windows setup inside the VM and prepares its Standard user account. Retain actual
creation/guest observations before attempting the install/upgrade matrix. Logs and source
hashes: .runtime/p0-05-vm-setup/validation.json and unit/lint/syntax/real_preflight.log.

## Resumed VM prerequisite inspection (2026-10-28)

The preceding conceptual VM explanation made no implementation progress. Fresh inspection
now changes the next action: New-VM/Get-VM resolve from Hyper-V and vmms is running.
Get-VMHost, Get-VM and Get-VMSwitch all fail with Access denied in this managed session.
No ISO is present in .runtime/windows-vm or the Downloads ISO listing; the intended
.runtime/vm-tests/Studio-Release-Test directory is absent. This does not prove that no VM
exists elsewhere: provider enumeration is denied. No mounted filesystem drive beyond C
is reported. Host feature availability is no longer the missing-command blocker.

Review the actual pending P0-05/P1-07 contracts and the remaining review/routing/optimization
gates. No qualified independent increment is newly actionable. Update the VM guide to skip
repeating feature installation when commands exist, request a normal administrator-session
provider result and the ISO path, and retain the standard-user guest matrix. No elevated
action, access-control change, VM mutation, application change or acceptance checkbox closure.
No tests are run for this documentation/environment observation; no live test handle exists.
Continuous goal remains active; the resumed blocked audit starts afresh. Evidence:
.runtime/roadmap-gates/20261028-resumed-vm/audit-1.json.

Second resumed audit: Get-VM still returns Access denied; the intended VM directory and
ISOs in the two documented locations remain absent. Saved4B review benefit and routing
quality gates remain false. No actionable independent increment or live test handle is
available. This is no progress, not a running-test wait; no tests or acceptance changes.
Evidence: .runtime/roadmap-gates/20261028-resumed-vm/audit-2.json. Owner provider results
and ISO path remain required; continuous execution stays active at this second audit.

Third consecutive resumed audit confirms Get-VM Access denied, no ISO in either documented
location and no intended VM directory. No new owner setup result or independent qualified
candidate is available. There is no running test handle; the last turn was no progress.
Continuous execution is blocked, not complete, until an external prerequisite changes.
No test, host mutation, security relaxation or checkbox closure. Evidence:
.runtime/roadmap-gates/20261028-resumed-vm/audit-3.json. Resume with the normal administrator
provider results and ISO path/guest setup from docs/windows-test-vm.md.

## Remaining-dependency audit after4B review (2026-10-27; first unchanged audit)

The previous goal turn made progress by completing the distinct4B review measurement.
Fresh read-only checks still find no New-VM/Get-VM management commands or Windows ISO in
the intended workspace/Windows downloads. Ollama lists only the same9B,4B and embedding
model identities. The owner's administrator setup result and ISO path remain pending.
Both review candidates fail benefit;4B also fails routing quality, prior server optimization
fails nonregression, and no optional new input need is selected. No safe independent
increment has all prerequisites satisfied. No test handle remains running; this is not a
background-test wait. No host/application changes, repeated tests or newly checked boxes.
Evidence: .runtime/roadmap-gates/20261027-after-4b-review/audit-1.json. Goal remains active
on the first unchanged audit; next action is the documented separate-VM owner setup.

Second unchanged audit: New-VM remains unavailable and no matching ISO appears in the
intended workspace/Windows downloads. Fresh model metadata matches the three prior digest
identities; saved review/routing/optimization gates remain false. No pending test process,
new application change, test rerun or checkbox completion. Evidence:
.runtime/roadmap-gates/20261027-after-4b-review/audit-2.json. External owner setup remains
the required next action; this turn is no progress, not a verified background wait.

Third consecutive unchanged audit: fresh managed-session New-VM lookup is still absent,
no intended Windows ISO is found, model digests are unchanged, and recorded specialist,
routing and server-optimization gates remain false. No test handle is running and no safe
independent increment has become actionable. Continuous execution is blocked, not complete;
resume on owner VM setup/ISO information or another genuinely changed prerequisite. No
host/application mutation, extra test run or acceptance closure. Evidence:
.runtime/roadmap-gates/20261027-after-4b-review/audit-3.json and vm-check-3.json.

## P2-04 new4B read-only-role trial completed without benefit (2026-10-27)

The new model's unchanged protocol2 trial completes24 paired inputs/72 ordinary role
calls with no incomplete workers. Exact-location oracle results: baseline17/24, self-review
20/24, specialist20/24. Specialist has zero wins over self-review and zero regressions;
the strict improvement gate is false. It also does not exceed retained9B self-review21/24.
This measures a distinct4B completion/schema-only role, not a retry of its tool-workflow
failures or the9B review candidate. No prompt, fixture, oracle, bound or accepted input is
retuned; complete settings/corpus hashes match the retained9B protocol2 manifest.

Independently reaggregate all24 observed records and match each to its successful bounded
worker's JSON output. Verify identity, source/grants, one child call/three total calls,
384-token output bounds, no mutations/delegation, source hashes and12/12 balanced order.
All application/test sources remain unchanged; previous unit contracts are not rerun for
an evidence-only model measurement. Actual24-input trial is complete; no skipped case
is counted. The native generation observation is3562 tokens/33.864582s (105.18 tokens/s).
Workflow p50/p95: baseline7.021/7.986s, self-review7.668/8.877s, specialist7.625/8.941s.
Mean specialist second-pass overhead versus self-review is+0.0415s. Those times exclude
worker start/cleanup and are not a paired9B/4B speed comparison or general review accuracy.

Keep P2-04 main unchecked; no Studio child, routing/default change or new permission grant.
Both measured review candidates fail the existing benefit requirement. Trial process exits0
because coverage completed, not because the specialist qualified. No owned trial remains
running. Evidence: .runtime/p2-04-4b-review/validation.json, plan.json, result.json and
trial-a8d4a2f1d0104011be50f727ff080af9; after.zip contains content-free summary/provenance
and operator source, not private reports/prompts. Fresh VM check still finds no New-VM
command or Windows ISO in the intended workspace/Windows downloads. Owner administrator
Hyper-V step/ISO/guest setup remains required; docs/windows-test-vm.md is the next action.

## P2-04 new4B read-only-role feasibility trial (2026-10-27; running)

VM management commands/Windows ISO remain unavailable on the fresh continuation; the
owner's requested host setup is still pending. Inspect actual review_trial.py, tests and
protocol2 documentation. The existing trial requires completion/structured output only,
not the tool workflows that failed4B routing qualification. A new installed model therefore
makes one distinct role-specific measurement actionable without new downloads or product
changes. This does not override the failed general-agent quality gate or retry its workflows.

Preregister .runtime/p2-04-4b-review/plan.json: same eight shipped fixtures/three repeats,
24 paired inputs/72 ordinary model calls, counterbalanced role order,384-token/30-second
per-role budgets and unchanged strict source-location/no-regression gate. Assert protocol,
corpus and complete settings hashes equal the retained9B protocol2 manifest; only model
identity/digest changes. Use a dedicated configuration/scopes and the validated bounded
read-only installed-idle guard before each worker. Preserve all outcomes and do not enable
delegation. A positive within4B comparison alone would not establish benefit over the
existing default9B baseline or complete integration/permission/cleanup acceptance.

The existing runner is now executing this first4B review trial; source hashes and case
artifacts are retained under that directory. No application/test source changes, default
change, broad regression repeat, VM alteration or adoption claim. Results remain pending.

## P2-05 second-candidate evaluation completed; no routing adoption (2026-10-27)

The approved4B candidate's first actual executions complete the unchanged20-case/three-
repeat matrix:53 passed,5 failed,2 blocked. All eight safety cases pass, every effect
observation is clear and no unauthorized effect is observed. Two browser-navigation result
checks and all three missing-file recovery artifact checks fail. Two harmless-draft tasks
remain terminally blocked even though their independent draft/fill/no-post checks pass;
do not promote those terminal outcomes to success. No failed or blocked executed workflow
is retried. Strict quality success_rate remains null because two rows are blocked; the
quality gate is false. Do not adopt routing or change the9B default.

The initial626.281s run records47 passed/3 failed/10 blocked, with metrics for52 actual
model executions. Eight slots never reached execute_case: installed-idle observation hit
transient journal/snapshot assertions, returning the parent's default blocked constructor
row without worker directory, latency or metrics. Reproduced a transient assertion followed
by stable reads. Fix only the development snapshot observer to retry unstable observations
for at most two seconds, retaining no-WAL/SHM and stable-hash requirements. Active tasks
still block immediately; no database/model authority is widened. Three guard tests pass,
zero skips, including active-task refusal and persistent-observation timeout.

Retain the original report unchanged. Independently verify exactly eight pre-dispatch slots,
then execute each once in fresh scopes using identical model digest/settings/corpus/oracles.
Those produce six passes/two failures. Consolidated observations retain every other original
sample byte-for-byte; all68 observations revalidate against their per-case sample files and
the existing aggregator. This is a completed matrix of first executions, not a second attempt
or a single uninterrupted run. Metrics cover60 samples:25863 generated tokens/291 calls,
weighted native generation110.22 tokens/s, task p50=11.782s/p95=13.953s. These pooled timings
are not a matched9B comparison and do not establish routing benefit. Source hashes remain
unchanged, final installed Studio idle check passes and private snapshots are removed.

Record second-candidate measurement prerequisite complete, keep P2-05 main unchecked.
Three actual capability cases and three guard cases pass; Ruff across local_agent/tests
passes. No broad regression rerun for unchanged application/test sources. Evidence:
.runtime/p2-05-candidate-4b/validation.json, original evaluation-c7e1084c4ea24657ad7ecbede3f64b01,
unexecuted-slots/provenance.json and completion-summary.json; after.zip retains operator/
configuration/report evidence without private prompts or case bodies. Next actionable
release dependency: owner Hyper-V enablement/ISO/guest setup in docs/windows-test-vm.md.
No owned evaluation process remains running; VM installation and routing acceptance remain open.

## P2-05 approved4B acquisition and capability checks (2026-10-27; quality run in progress)

Owner explicitly approves qwen3.5:4b download/evaluation and requests a separate VM. The
existing pull-model.ps1 succeeds, exit0. Installed local GGUF is4.2B/Q4_K_M,3324173934
bytes, manifest d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04;
Ollama0.40.7 advertises completion/thinking/tools/vision. Current installed default remains9B.
Metadata alone is not capability or quality proof. Actual reused live tests then pass3/3,
zero skips,14.639s: structured schema plus observed GPU allocation3364911840 bytes at8192
context, real write tool/readback/followup, and correct synthetic red-image recognition.

Created a dedicated candidate configuration/workspace/state; no production configuration
is changed. Initial read-only direct SQLite idle query could not open the installed database
under managed access. Use the established consistent read-only private-copy observation,
with no WAL/SHM allowed, stable pre/post hashes and exact temporary-file removal. Guard the
installed Studio before admission and every model sample, alongside the evaluator's own
idle guard; no production database writes or stale snapshot reuse. A development smoke
script initially lacked the repository tests import path; fixed its path, then all three
real cases execute successfully. No application/test-source modification or skip.

The unchanged corpus dc25226fa4dfd447f0820753d9931fa9bb77d66872244a1cbb86e3318ff68457
is now running60 actual model attempts and eight safety cases. All safety cases have passed;
model outcomes remain pending. Evidence/config/approval/run-reference and live artifacts are
in .runtime/p2-05-candidate-4b/. No routing/default change or quality success is claimed.
P0-05 fixture preparation is complete at build scope; actual VM setup/release testing is
externally pending while this independent evaluation proceeds.

## P0-05 separate-VM and actual-version upgrade preparation (2026-10-27)

Owner requests a separate VM and explicitly approves qwen3.5:4b download/evaluation while
retaining the current default. Record approval in .runtime/p2-05-candidate-4b/approval.json.
Readonly host inspection reports Professional edition,443.3GiB available; vmcompute/hns
are running, but no Hyper-V management commands, WindowsSandbox executable/package,
VirtualBox or VMware provider is found. Firmware capability query is denied, so support is
unverified rather than declared absent. No host feature/VM is changed. Added the reviewed
Hyper-V/Windows11/standard-user setup and acceptance matrix in docs/windows-test-vm.md;
both PowerShell blocks parse without syntax errors, but actual provider execution is untested.
Official Microsoft documentation confirms generation2/Secure Boot/vTPM configuration and
the separate administrator feature-enablement step. Owner ISO/guest setup remains required.

A same-version reinstall would not prove upgrade. Created an isolated fixture source/target
under .runtime/p0-05-install-upgrade-fixture, copied existing frontend/backend, and changed
only its package/version metadata to0.1.1 plus disabled the fixture frontend rebuild hook
because its exact built assets were copied. Original checkout, version, assets and NSIS
remain byte-identical. Real offline Tauri/NSIS build succeeds. Baseline installer74098719
bytes/SHA904b5a0010f258ce4acc2a57851e32c2f37df22777f066dbeef768de523103f7;
upgrade fixture74101660 bytes/SHA364f519ef0b0533ddef155369d53f4e6260c313423aade8e352e75a223d08bef.
Neither installer is executed on the host. Artifacts are in that case's artifacts directory.

Initial Rust run passed5/failed2 because copied-source lifecycle tests expect a test Python
environment at their fixture root. Supplied a copied Python launcher/config and a test-only
site path to the existing trusted dependencies; no product/test implementation was changed
or skipped. All seven then pass, zero ignored,0.90s test execution. This developer environment
is outside the packaged release and is not VM/isolation evidence. Build source/readback
hashes and original-input preservation are in inputs.json/build-result.json; source builder
and logs are retained. Mark the artifact prerequisite only; P0-05 third stays incomplete.
Next: owner enables Hyper-V/provides ISO and installs guest, then executes the documented
standard-user0.1.0→0.1.1/history/uninstall matrix. The0.1.1 fixture is not a production release.

## P0-05 native screenshot capture and preview verified (2026-10-27)

Owner explicitly confirms the screenshot preview appears after the installed camera/Capture
and preview flow. Inspected frontend capture/preview requests, confirmed screenshot API and
attachment normalization, then took a consistent read-only installed-state metadata snapshot
without constructing/migrating the production Store. Two images newer than the baseline
are named screenshot.jpg and decode/verify as JPEG,1600x900. Stored byte counts match
141558 and136112 bytes; hashes are recorded in the content-free validation artifact.
These attachments are not bound to messages; no model-image submission or image-recognition
claim follows this capture/preview check.

No screenshot was displayed to the agent or exported. Only format, dimensions, sizes, hashes
and generated-name/binding checks were retained; temporary private SQLite copy removed.
Native rendering is owner-observed; persisted capture metadata is independently checked.
No application/configuration/model changes or regression reruns for this evidence-only
update. Prior62-check operator regression remains its own separate evidence.

Mark the native capture/preview subcheck complete. Keep P0-05 third unchecked for tested
clean standard-user installation, upgrade with configuration/history retention and actual
uninstall/data behavior. This needs an appropriate disposable Windows test environment;
the production account/install is not a clean fixture. Other VM/model/benefit prerequisites
remain separate. Evidence: .runtime/p0-05-native-capture-acceptance/validation.json,
observe.py and after.zip. Next actionable release increment: provision/use the approved
separate standard-user test environment and perform the documented install/upgrade checks.

## P0-05 native independent-Ollama preservation verified (2026-10-27)

Owner completes the corrected operator's native CONNECTED and X/CLOSED flow. Loaded saved
report1d6ac6dd25ce42ce824c8b54a294e4a0 and checked the exercised scope against actual operator
source. The separately owned Ollama fixture2208 retains its PID/creation time, listener
and bounded version health across installed Studio16816's normal close. Captured native
descendants exit before harness cleanup. Owner confirms visible connection and X close;
process/listener/health observations are collected by the tested operator. Its own fixture
is intentionally cleaned up only after survival is verified; it is not a preexisting user's
service and is not claimed to remain running after the harness exits.

Fresh independent verification matches the operator/tests to the prior62-check regression
source hashes and current installed native/backend to the release-manifest/report hashes.
No Studio/backend/Ollama images or17861/11434 listeners remain; fixture identity is gone,
consistent with the report's successful owned cleanup. Original failed startup report is
retained. No application/configuration/model edits, process starts/stops or new regression
execution were needed for this evidence-only update.

Mark the normal-close independent-Ollama subcheck complete; P0-05 third stays unchecked
for native capture/image preview and clean standard-user install/upgrade/history/uninstall.
Evidence: .runtime/p0-05-native-shared-model-acceptance/validation.json, verify.py and after.zip.
Next: reopen installed Studio and exercise camera/Capture and preview; obtain the owner's
native preview observation without inferring it from component tests or metadata alone.

## P0-05 shared-model checker startup race corrected (2026-10-27)

Owner run b6e96971f4344ac1b0b93136bddf81b1 failed with independent_model_not_healthy before
native launch and cleaned up successfully. Inspection found the operator treated a newly
bound listener as immediate HTTP readiness. Reproduced on an owned private-port Ollama:
the original prepare failed, but the same live process/identity became healthy later
(observed at3.547s). This demonstrates a checker defect; the owner's compact report alone
does not distinguish every possible health failure.

Correct scripts/native-shared-model-check.py to wait for its own fixture's HTTP health
within the existing20-second startup budget. Keep one process, verify identity around the
probe, fail immediately on ownership changes/process exit, and leave preexisting services
on the existing fail-closed/no-restart path. Report the current phase, fixture/existing
source and known process identity even when startup fails. No application/configuration/
model changes, installer rebuild or security relaxation.

Two new regression cases cover delayed health, health deadline and changed ownership;
19 operator tests plus lifecycle/runtime/process/package/discovery regression:62 passed,
zero skips,14.439s. Ruff passes across local_agent, tests and both operator scripts. A real
owned private-port startup passes with the fix (ready at2.547s) and owned cleanup succeeds.
No latency improvement is inferred from these individual startup observations. Managed
model-store access-denied log categories persist; health does not certify inference or
native UI acceptance. Original failed owner report and before/after observations retained
under .runtime/p0-05-shared-model-startup/, with validation.json and after.zip.

Keep P0-05 third/native shared-Ollama preservation unchecked. Next: rerun the same operator
command in normal PowerShell, confirm CONNECTED, then close using X and confirm CLOSED.
Capture/preview and tested clean-install/upgrade/data acceptance remain separate.

## Remaining-dependency audit after native operator support (2026-10-27)

Read current documents, pending roadmap requirements and saved failed benefit gates, then
rechecked external state without starting/stopping services or modifying production state.
Installed Studio/backend PIDs are live; no passed shared-Ollama operator report has appeared.
A consistent read-only installed snapshot still contains zero image attachments and no active
tasks; private snapshot is removed. Existing Ollama metadata responds and lists the same9B
completion and0.6B embedding models. No new download permission is received; Get-VM,
VBoxManage and vmrun are unavailable, with no configured disposable VM/image established.
Specialist/optimization gates remain failed; optional document/OCR demand is unspecified.

No remaining implementation increment has all dependencies satisfied. This is the first
unchanged-blocker audit after the prior operator implementation made progress, not a native
pass or a running background test. Corrected the stale current-blocker table/installer guide
in ROADMAP.md: completed SDK/MCP, embedding integration and NSIS building no longer appear as
remaining acquisition work. All incomplete acceptance checkboxes remain open. No application
changes or repeated regression suites; the60-check operator regression remains the latest
applicable result. Evidence: .runtime/roadmap-gates/20261027-after-native-operator/gates.json.
Next: owner capture/preview and the documented native shared-Ollama exercise; clean install/
upgrade requires an appropriate separate standard-user environment. Goal remains active.

Second consecutive dependency audit: same installed Studio/backend process identities,
zero image attachments, no passed native operator report, the same two model identities
(one completion candidate), and no available VM command/provider. No new user approval or
input has arrived. This is unchanged external blockage, not implementation progress or a
background-test wait. No application edits or regression reruns. Evidence:
.runtime/roadmap-gates/20261027-after-native-operator-audit-2/gates.json. Requirements remain
unchecked; goal remains active pending the blocked-audit threshold or changed prerequisites.

Third consecutive audit confirms the same live native process identities, zero new images,
no passed shared-model report, unchanged single completion candidate and unavailable VM
commands. No running test handle is being awaited. Evidence:
.runtime/roadmap-gates/20261027-after-native-operator-audit-3/gates.json. No safe independent
increment has become actionable; continuous execution is blocked pending owner native
observations, approved candidate acquisition or a configured test/isolation environment.
The previous operator increment remains verified at60 checks/zero skips; no new tests were
run for this documentation-only audit. P0-05 third and all other incomplete gates stay open.

## P0-05 third independent-Ollama native acceptance support (2026-10-27)

Inspected the installed-native recovery operator, process ownership/output code, trusted
Ollama launch/configuration, relevant lifecycle tests and authoritative documents. The
application already connects to existing Ollama without owning it; the gap is native
normal-close verification. Added scripts/native-shared-model-check.py and17 tests, reusing
the existing operator's package hashes, process identity, native observation and bounded
console confirmation helpers. No application/frozen code, configuration or model changes.

The new operator refuses an existing Studio or backend-port collision. It reads trusted
installed configuration without migrations/writes and supports the default literal model
listener. It connects to an existing Ollama or starts a separately owned configured fixture;
ownership must be established before health requests. The actual native connection and X
close require owner observations. Same PID/creation time, listener and bounded GET version
health are checked before/after closure; captured native children must exit before cleanup.
Only its own fixture/native jobs are closed, independently even on errors. No model load,
unload, download, prompt, raw output or credential export. A ready preflight or fixture test
cannot establish native acceptance.

Verification:17 new tests plus the existing recovery, native diagnostic, process output,
runtime, release-manifest and discovery contracts:60 passed, zero skipped,12.811s. Ruff
passes across local_agent, tests and both native operator scripts. Development tests exposed
two fixture assumptions (the actual Denied exception type and a missing simulated launch
PID); corrected those fixtures and reran the complete relevant set. Real loopback tests
cover version/redirect/oversized responses and a dripping-header deadline; real process
fixtures verify owned cleanup with an unrelated process surviving. These are component
observations, not certification of the installed window.

Actual --exercise returned existing_studio_preserved with owned_cleanup=true and no launches;
the owner's open Studio remains untouched. Report:
.runtime/native-shared-model-8748cd3d808643adaef2c5cd069872e8/report.json. Current installed
native/backend hashes still match the release manifest. Evidence/source snapshot:
.runtime/p0-05-native-shared-model-harness/validation.json and after.zip. Physical capture
is also pending: consistent read-only metadata observation finds no new image attachments;
private SQLite snapshot removed, no image/transcript exported. See
.runtime/p0-05-native-export-acceptance/capture-observation.json.

Keep P0-05 third unchecked. Next: owner completes Capture and preview, then closes Studio
and runs the two-prompt normal-session check in docs/native-shared-model-check.md. Tested
clean-install/upgrade/history/uninstall, the VM prerequisite, unanswered second-model
download approval and failed specialist/optimization benefit gates remain separate.

## P0-05 third native Markdown export/download verified (2026-10-27)

Owner reports Export prepared two messages/208 UTF-8 bytes. Independently identify the
fixture's conversation from a consistent read-only installed-state copy, then run the
production history.export_markdown function against a read-only snapshot adapter without
constructing/migrating the production Store. The resulting complete two-message transcript
is208 bytes, contains the assistant's marker reply, and omits the full attachment body.

The exact expected conversation-1686b09501f748cfb3078d7a0386600b.md exists in the owner's
Downloads directory. Stable readback matches the complete expected bytes and SHA256
2b95d78ee5ba571ed902e39d155b9ea59c2e3a194b97fc3eda3b9d9410940f2c. This verifies actual
native delivery beyond the application's notification. No user file was modified; raw
transcript text was not copied into diagnostics and private database snapshots are removed.
No Save As dialog is claimed: delivery was observed in default Downloads.

Evidence: .runtime/p0-05-native-export-acceptance/installed-observation.json, validation.json
and observe.py. Mark native export/download subcheck complete; full third remains open.
No application/configuration/model change or regression-suite rerun. Next: owner exercises
native Capture screen and confirms its image preview; native shared-Ollama preservation and
tested clean installation/upgrade/history/uninstall remain separate requirements.

## P0-05 third native file-picker/text attachment subcheck verified (2026-10-27)

Owner supplied the correct fixture marker and explicitly confirmed the paperclip opened
the Windows file chooser and selected the file successfully. Independent read-only installed
state inspection finds the87-byte attachment's sanitized UTF-8 text matches the original
benign fixture, SHA256c14a90e5de45c8017ae623974d6fa5f17542b623d71544d271f415e3be8c42db.
It is bound to the user message; the corresponding Chat task is reported and its assistant
reply contains the expected marker with one real model call/25 generated tokens. No active
task remains. Picker/reply rendering are owner-observed; data binding and metrics are
independently verified. Mark this subcheck complete; full third remains open.

The observer first incorrectly expected a raw attachment byte blob. Source confirms text
attachments intentionally retain sanitized text with an empty raw blob; corrected comparison
to the stored text. A later unrelated live-service probe encountered connection refusal
after durable checks passed; removed that nonessential probe without restarting any service
or claiming current live availability. The final durable readback passes; both initial
observer issues were diagnostic-script assumptions, not application failures. Temporary
private SQLite snapshots are removed; raw text/prompt/credentials were not exported.

Evidence: .runtime/p0-05-native-attachment-acceptance/installed-observation.json and
validation.json, with the explicit owner confirmation recorded separately. No application/
configuration/model changes or regression-suite rerun. Next smallest third-increment
native flow is conversation export/download; physical capture/preview, native shared-Ollama
preservation and tested installation/upgrade/history/uninstall remain separate gaps.

## P0-05 first increment completed with installed native evidence (2026-10-27)

Owner completed the retry/fallback/normal-close exercise; independently loaded the saved
report e7420e8c254e4ef59feb27380e4dc20f and checked its assertions against the tested operator
source and current installed EXE/backend hashes. Initial plus three failed launches have
exit-to-start lower bounds1.094892/2.019097/4.047970s. The retry budget stops; owner confirms
visible port diagnostics/manual fallback, then connects through one manual fifth launch.
Normal close releases captured descendants before harness cleanup; independent Python
survives. Fresh system inspection finds no Studio/backend/Ollama images or17861/11434
listeners. Native UI observations are owner-confirmed; timing/process evidence is independent.

Requirement-by-requirement first-increment audit combines this run with earlier native
focus, EOF/normal close/reopen, idle/pending-approval crash, interrupted/no-replay/fresh
approval and component/frozen dependency/privacy fault checks. All first-increment criteria
are satisfied at these recorded scopes; mark first and retry/fallback subcheck complete.
P0-05 third remains open: physical attachment/capture/export dialogs, independent shared
Ollama preservation in the native close scenario, and tested install/upgrade/history/uninstall.
No broad claim covering every active-work effect or hostile-process isolation is made.

Build identity audit:117/118 manifest inputs match raw bytes. local_agent/patches.py differs
only by an EOF blank line; archived baseline matches the manifest and both ASTs are identical.
Preserved current file; did not rewrite metadata to hide the mismatch. Installed binary hashes
and tested operator source match exactly. Earlier unexpected_extra_attempt report438e02...
is retained; the successful owner run used unchanged helper code and criteria. New report
validation is acceptance evidence, not another automated regression-suite run; prior43
checks/zero skips remain historical evidence. No app/config/model/installer modifications.

Audit: .runtime/p0-05-native-lifecycle-acceptance/validation.json. Successful native report:
.runtime/native-recovery-e7420e8c254e4ef59feb27380e4dc20f/report.json. No repeat of completed
lifecycle steps is needed. Proceed to the smallest remaining third-increment physical UI
check while separate VM/model-candidate gates remain pending.

Prepared a new exclusive attachment fixture for that next check, without overwriting user
files: workspace/native-ui-check-39549fdb/attachment-check.txt,87 UTF-8 bytes, SHA256
c14a90e5de45c8017ae623974d6fa5f17542b623d71544d271f415e3be8c42db. Source inspection confirms
paperclip file selection uploads selected bytes and binds the attachment to the message.
Owner must exercise the real Windows picker and ask Chat for the marker value; neither
picker operation nor model attachment response is yet counted as verified. Steps/status:
.runtime/p0-05-native-lifecycle-acceptance/next-attachment-fixture.json.

## Owner retry check preserved the still-running instance (2026-10-27)

Owner ran the operator command; saved report native-recovery-f2c7ca8e0a8641a4b990e3fd8141a4f5
records existing_studio_preserved, zero attempts and native_acceptance=not_verified.
Independent process inspection confirms the original installed native16652 is still running
with backend30116/34340 and owned Ollama28688. No process was stopped or application changed.
Close that Studio window normally, wait for its children to exit, then rerun the command
without reopening Studio first: the helper launches its own test window. This confirms the
preflight refusal, not retry/fallback acceptance. Goal's existing blocked status and open
P0-05 criteria remain unchanged.

## Continuous execution blocked after native-harness audits (2026-10-27)

Three consecutive post-harness turns confirm the same prerequisites: no live operator
helper, no new native report, and existing_studio_preserved/not_verified remains the latest
result. No candidate-download approval or second completion model appeared; no disposable
VM provider/image became configured or discoverable. Specialist/optimization benefit gates
remain failed and optional document work has no selected input need. No safe independent
increment is actionable without new owner input or external-state change.

Continuous execution is blocked, not complete. The implemented operator check and43 passing
component/regression checks remain valid at their recorded scope; no test was repeated or
acceptance checkbox closed in these audits. Resume with the native check's final JSON, an
explicitly approved second-model acquisition, or a supported configured isolation target.
Native command: .\.venv\Scripts\python.exe .\scripts\native-recovery-check.py --exercise
from normal PowerShell with Studio closed. Evidence:
.runtime/roadmap-gates/native-retry-pending-audit-3.json. No running process was changed.

## P0-05 native retry/fallback operator harness (2026-10-27)

Post-harness prerequisite audit1: no live operator helper or new native report appeared
after rechecking; the existing report still records existing_studio_preserved. The same
two models remain installed, no second-model download approval has arrived, and VM
executables remain undiscovered. No safe independent increment became actionable. This
continuation is no implementation progress, not a verified process wait; the goal remains
active pending the required owner run. No tests were repeated or checkboxes closed.
Evidence: .runtime/roadmap-gates/native-retry-pending-audit-1.json.

Audit2 revalidates the same condition: no live helper/new report, unchanged models and
undiscovered VM executables, with no download approval. No safe independent increment is
available; no source behavior or test evidence changed. This is another no-progress turn,
not a verified wait. Goal remains active pending the native owner run. Evidence:
.runtime/roadmap-gates/native-retry-pending-audit-2.json.

Previous turn completed the fresh native approval scenario; this turn implements the next
verification prerequisite without changing application behavior. Read current requirements,
source and recovery tests. An initial concern about cancelled startup timers was not
reproduced: connecting starts true, and the real rendered recovery test passes1/1,14.749s,
including three1/2/4-second automatic retries, manual fallback and saved task state. No
speculative React recovery fix was made; browser-bridged IPC is still not native evidence.

Added scripts/native-recovery-check.py and docs/native-recovery-check.md. Operator must
close existing Studio first. The script refuses an existing instance, verifies installed
EXE/backend hashes against release metadata, reserves localhost17861 exclusively without
accepting/reading requests, and launches only its own installed test window. It observes
initial plus three failed backend launches, conservative process backoff lower bounds and
a six-second quiet window. Owner confirms visible port diagnostics/fallback, then the guard
is released for manual Restart backend. A new owned listener and owner connection are
required. Normal close must release captured descendants while a separate Python fixture
survives before fixture cleanup. Overall deadline, bounded content-free report, distinct
owned jobs and preserved private WebView profile apply; no task/API/tool/default is added.

Twelve new tests pass; combined native diagnostic/process-output/runtime/release/discovery
regression43/43 passes, zero skips,11.433s after the final cleanup hardening. Ruff passes
for application/tests/new script.
Real fixture deadline cleanup reaps owned parent/child, releases the guard and preserves
an unrelated process. Negative cases cover existing-instance refusal, no-launch preflight,
port collision, binary mismatch/hardlinks, process reuse/disappearance and cleanup failures.
Initial test/lint failures were fixed, including Windows lstat/fstat execute-bit differences
for .exe hashing; the helper compares regular single-link identity/bytes without changing
the application's file-review security checks. No frontend/backend rebuild is needed.

Actual installed hashes match the current manifest. Actual --exercise correctly refuses
the owner's still-running Studio with existing_studio_preserved, no process launch or stop;
native retry/fallback acceptance remains not_verified. Evidence/report pointer and source
snapshot are in .runtime/p0-05-native-retry-harness/validation.json. P0-05 first/third stay
unchecked. Next required input is a normal-session operator run of the documented command;
native timing/manual UI results, shared-Ollama preservation, physical controls and upgrade
must not be inferred from the harness tests or prior narrower checks.

## P0-05 fresh approval after native crash verified (2026-10-26)

Owner resubmitted the same Agent instruction after pending-approval crash recovery and
denied the new review. Independent read-only inspection confirms a distinct Agent task,
one new approval event and one false approval answer, completed write_file outcome=denied,
blocked terminal state and zero verifications. The interrupted task retains its original
unknown write intent, zero approval resolutions and zero verifications. No active task
remains; native-recovery-check/should-not-exist.txt is still absent.

The new task records two real model calls and59 generated tokens, corroborating model/tool
execution after this crash. All pre-resubmission conversation/task/message/verification
identity sets are retained. This completes the specific pending approval -> crash ->
interrupted/no replay -> fresh request/denial scenario, with native dialog use owner-observed
and durable decisions/state/file absence independently verified. It does not establish
retry timing/exhaustion/manual fallback, all possible active effects, unrelated-process
preservation, physical capture/export or upgrade acceptance. Full P0-05 first/third stay open.

Evidence: .runtime/p0-05-native-recovery-fresh-denial/installed-observation.json and observe.py.
Temporary private SQLite snapshots are removed. No application/configuration/model changes
or new automated regression-suite runs. Next remaining native lifecycle increment is bounded
retry exhaustion/manual restart verification; the previously checked lifecycle/approval
steps need not be repeated. Separate remaining physical/install/upgrade gates remain listed
in ROADMAP.md; no broad completion claim is made.

## P0-05 native pending-approval interruption/no-replay verified (2026-10-26)

Owner ended the identified listening backend with the review unanswered and reports the
native restart/interruption notice. Independent inspection matches the previously waiting
task ID to status/terminal_status=interrupted and the exact fixed restart notice. The
unapproved target is absent before and after. Its write_file journal entry is unknown,
outcome=null, with zero verifier references; preserve that conservative uncertainty rather
than asserting the intent was completed, rolled back or durably denied.

Zero approval resolutions, zero verifications and zero new task/operation/verifier records
appear since the pre-crash baseline. No active task remains. The original task worker28596,
backend2548/13304 and owned Ollama29428 have exited; the same native16652 now owns new
backend30116/34340 and Ollama28688, with one listener per service. The observer started/
terminated nothing. This verifies interruption without observed replay for this pending-
approval scenario; native retry timing/exhaustion/fallback and other active-work effects
remain separate. A full history identity baseline was not captured immediately before
this specific crash, so no additional all-history-retention claim is made from this run.

Evidence: .runtime/p0-05-native-pending-crash/pre-crash-observation.json,
post-crash-observation.json and validation.json. Temporary private SQLite snapshots are
removed. No application changes or automated regression-suite rerun. The narrow subcheck
closes; full P0-05 first/third remain open. Next: owner resubmits the same instruction,
observes a fresh approval and denies it; verify real post-crash generation, distinct task/
approval resolution and continued target absence without granting the old request.

## P0-05 pending-approval crash test baseline captured (2026-10-26)

Owner reports the native review dialog is open. Read-only pre-crash observation confirms
one Agent task waiting, one unresolved approval, zero verifications, and a write_file
operation committed as intent with no outcome. The unapproved target is absent. Recorded
native16652, backend2548/13304, task worker28596 and owned Ollama29428;13304 owns the
backend listener. This is a baseline, not a recovery/no-replay pass. Next owner action is
to end only the identified listening backend13304 while leaving the approval unanswered
and native window open. After reconnect, verify interrupted task, retired worker, absent
target and no approval reuse. Evidence:
.runtime/p0-05-native-pending-crash/pre-crash-observation.json. No application changes,
observer process termination or new completed acceptance checkbox.

## P0-05 installed idle backend-crash recovery verified (2026-10-26)

Owner ended the identified idle backend process and reports automatic reconnection.
Independent post-recovery inspection confirms the same native16652 remains, previous
backend9948/2204 and owned Ollama1384 are gone, and a new backend pair2548/13304 plus
owned Ollama29428 belong to that native instance. One loopback backend listener and one
model listener exist, with no persistent duplicate. The observer killed/started nothing.

All pre-crash conversation/task/message/verification identity sets remain, including the
denied/approved operations and exact18-byte artifact. There are zero new tasks, operations
or verifier records after the baseline and zero active tasks. This corroborates idle
recovery without observed task replay; it does not test interruption/replay of active work.
Owner observes reconnection; native retry timing/exhaustion/manual fallback were not measured
in this post-event snapshot. No new generation after this particular crash is claimed from
model-list metadata alone. Full P0-05 first/third remain open.

Evidence: .runtime/p0-05-native-idle-crash-recovery/process-observation.json,
installed-observation.json and validation.json. Temporary private database snapshots are
removed. No application changes/dependencies/regression-suite runs. Next: exercise recovery
with an unapproved pending file creation, then verify interrupted state, no file/no replay,
fresh approval requirements and real generation. The proposed target
native-recovery-check/should-not-exist.txt is absent before that test; no request or write
has been made by the observer. Physical controls, unrelated-process preservation and
tested upgrade remain separate gaps.

## P0-05 normal reopen/generation and persisted history verified (2026-10-26)

Owner reopened installed Studio and supplied the visible model reply. Fresh read-only
inspection verifies native16652 -> PyInstaller9948/2204 -> owned Ollama1384, with loopback
listeners17861/11434. The observer started/stopped nothing; the prior close had left no
model listener. This corroborates normal application-managed backend/model startup without
separate terminals. The post-reopen task is Chat/reported, one model call and13 generated
tokens; zero tasks remain active. The reply is not exactly RESTART-OK, so this proves
generation/rendering, not exact-response compliance. Model prose asserting a system reset
does not establish an application reset.

Compared sorted pre-close identity/count baselines using creation-time cutoff: the original
conversation, two tasks, four messages and artifact-verification record all remain. Both
denied/approved operations and the exact18-byte file still validate. This proves persisted
record retention across normal reopen; owner has not explicitly confirmed rendering of
the older transcript, and no upgrade or crash-recovery acceptance follows from this check.

Evidence: .runtime/p0-05-native-reopen/installed-observation.json and process-observation.json.
Temporary private database snapshots are removed. No application changes, new dependencies
or regression-suite runs. Full P0-05 first/third remain open; next native lifecycle check is
controlled idle backend-crash recovery with bounded retries, fresh process ownership and
retained history, then separate active-task/no-replay and unrelated-process-preservation
checks. Physical capture/dialog/export and tested upgrade remain outstanding.

## P0-05 installed normal shutdown verified (2026-10-26)

After the owner closed installed Studio using X and left it closed, independently checked
the recorded PID/create-time baseline. Native20520, PyInstaller28820/12868 and owned
Ollama27952 have all exited; ports17861/11434 have no listeners. No Studio/backend/Ollama
image remains in the process snapshot. The observer did not terminate or restart anything.
Source review confirms native Exit sends shutdown and the backend lifespan closes its
manager and owned model service. This normal idle-close check passes at the observed scope.

Shutdown duration was not timed. No independent Python/Ollama process was present in the
corrected pre-close baseline, so unrelated-process preservation is untested by this native
run. Crash recovery, shutdown during active work, physical capture/export and upgrade remain
separate acceptance gaps. Full P0-05 first/third remain open. No application changes or new
automated regression-suite passes are claimed for this evidence-only update.

Evidence: .runtime/p0-05-native-normal-shutdown/observation.json and installed-observation.json.
Read-only stopped-state inspection preserves both approval outcomes and the exact18-byte
artifact, records content-free history identity/count baselines for reopening, and does not
start/contact Ollama. Temporary private database snapshots are removed. Next: owner reopens
Studio normally, confirms prior conversations render and sends a Chat reply request; inspect
automatic model startup and preserved history against this baseline before crash testing.

## P0-05 installed second launch focuses existing instance (2026-10-26)

Owner launched installed Studio again and observed the existing window gaining focus.
Fresh read-only process/listener inspection finds the same original native PID20520,
PyInstaller parent/child28820/12868 and owned Ollama27952, one native process and one
backend listener on loopback17861. The two backend images form the existing PyInstaller
parent/child pair; they are not duplicate listening services. Model listener11434 also
retains its original owner. Source registers tauri_plugin_single_instance before setup
and focuses the existing main window. No application or process modification was needed.

This closes the specific owner-observed focus/no persistent duplicate subcheck. The process
snapshot is after the launch, not a continuous trace proving no transient process existed.
Native recovery/shutdown/upgrade checks remain open, as do full P0-05 first/third increments.
No regression suite was rerun for this evidence-only update. Content-free installed-state
inspection confirms zero active tasks and retains both approval-test task outcomes.

Evidence: .runtime/p0-05-native-second-instance/observation.json and installed-observation.json.
Prepared shutdown-baseline-final.json for the next owner-initiated normal close; observer
ancestors are excluded. The earlier baseline is superseded because it included an observer
ancestor. No independent Python/Ollama process remains in the corrected baseline, so this
baseline alone cannot establish unrelated-process preservation. No shutdown has occurred or
been claimed. Next: owner closes Studio, then inspect the recorded owned PIDs/listeners
before reopening. Native physical dialogs/capture/export and tested upgrade remain separate.

## P0-05 native file approval acceptance verified (2026-10-26)

Owner completed the corrected Agent-mode deny/resubmit/approve sequence in installed
Studio. Independent read-only installed-state inspection confirms two distinct Agent
tasks: the first is blocked with approval_resolved=false, write_file outcome=denied and
zero artifact records; the fresh task is reported with approval_resolved=true, write_file
outcome=observed and one validated passed artifact record. No active task remains.

Independently read the existing approved test file without modifying it: exactly18 bytes,
NATIVE-APPROVAL-OK, SHA256
6a3fa6bc830cea79233157ea45342856c0705c1981fb10777ca379e9179630dd.
The durable verifier's expected/observed byte counts and hashes match that independent
readback. Dialog operation is owner-observed; backend decisions, journal outcomes and
artifact bytes are independently corroborated. This establishes the specific native
approval workflow, not all native or clean-install/upgrade acceptance. The earlier absent
file observation preceded these tasks; post-run inspection alone is not proof of the
filesystem at every instant during denial.

Evidence: .runtime/p0-05-native-approval-verified/installed-observation.json and observe.py.
The first observer attempt rejected Windows backslashes in the artifact label; normalized
separators for this known-label comparison, then reran successfully. No application failure
or source fix was involved. Temporary private SQLite snapshots were removed. No application
code/configuration/model/process changed, and no automated regression suite was rerun for
this evidence-only update. P0-05 first/third remain open; next native acceptance is the
second-instance check, followed by owned shutdown/recovery and upgrade/history checks.

## Native approval attempt diagnosed as Chat mode (2026-10-26)

Owner supplied a cancelled response followed by a model refusal to create files. Fresh
content-free installed-state observation confirms both recent tasks used mode=chat:
one cancelled, one reported, with zero active tasks. Frontend App.tsx submits the selected
sidebar view as task mode; worker.py's chat branch does not dispatch agent tools. This
attempt therefore does not test approval denial or approved file creation. ActionApproval.tsx
has separate Deny and Approve action buttons; Stop cancels work instead of denying a
specific approval. No application change or new test pass is inferred. Retry in a fresh
conversation after selecting Agent, with Coding only or Unified tool access; deny the first
actual review dialog, then resubmit and approve the fresh request. Evidence:
.runtime/p0-05-native-approval-mode-check/installed-observation.json. Native acceptance and
roadmap checkboxes remain open; existing blocked goal status is unchanged.

## Continuous roadmap blocked audit 3 (2026-10-26)

Revalidated the remaining increments after three consecutive turns with unchanged
prerequisites. The preceding turn confirmed previously recorded owner verification of
Reply/Copy/Stop; it made no implementation progress and was not a verified process wait.
Fresh content-free installed-state observation shows zero active tasks, the same reported
and cancelled chats, Ollama0.40.7 and only qwen3.5:9b plus the embedding model. The native
approval target remains absent; no deny/resubmit/approve result has been received. No
application, configuration, model or running service was changed.

P0-05 native approval/recovery/upgrade acceptance still requires interactive owner evidence.
P2-05 lacks a second evaluated completion model; explicit qwen3.5:4b download permission
remains unanswered. P1-07 lacks a configured disposable VM/provider. P2-04 and P3-02 retain
their failed benefit/nonregression gates, and P3-01 has no selected input need. Repeating
completed tests or failed candidate trials would not satisfy these missing prerequisites.
No tests were rerun or counted as newly passed; no roadmap checkbox was changed.

Continuous execution is blocked, not complete. Resume after the native approval result,
explicit candidate-download approval, or a configured supported isolation prerequisite
changes. Evidence: .runtime/roadmap-gates/native-pending-audit-3/installed-observation.json
and prerequisites.json. The private temporary database snapshot was removed.

## Native acceptance/model-routing prerequisite review (2026-10-26)

Previous goal turn was verified progress: normal installed inference/browser/memory recovery
and the NSIS payload manifest correction. This continuation re-read the requirements and
checked current installed state. Updated sidecar SHA still matches; the native approval
target is absent. A content-free consistent installed-state observation records a completed
cancelled chat in addition to the earlier reported chat, with no active task. This supports
the owner's Stop confirmation; it is not a file-creation approval pass. The requested
Agent deny/resubmit/approve test remains pending. No application/installer/model/default
was modified and no completed regression was rerun.

Assessed the independent P2-05 dependency instead of inventing routing before prerequisites.
There is still only one installed completion model; the embedding model is not a substitute.
Official Ollama model/tag pages now verify qwen3.5:4b exists, advertised with vision/tools/
thinking and3.3–4.0GB variants. Runtime format/compatibility and performance are unverified;
the current9B manifest/default is retained. Available disk is about461.8GB. Reviewed the
installed0.40.7 pull help and actual evaluation CLI: candidate evaluation uses a dedicated
--config, not a nonexistent --model flag. The fixed corpus has20 model cases/3 repeats and
8 safety cases, with unchanged oracles and all outcomes retained. New model identity,
capabilities/structured output and any measured task-type benefit must pass before routing.

Prepared a concrete download/evaluation plan at .runtime/p2-05-second-model-readiness/plan.json
and asked for explicit candidate download approval under ROADMAP's user-approved-download
requirement. No download or evaluation has started; elapsed time is not permission. Future
evaluation must check installed Studio idleness, preserve shared service/9B defaults and
distinguish warm/load observations without explicit shared-service unload/restart. No new
checkbox is complete. Native approval evidence or approved second-model acquisition is
the next external input; VM setup and failed specialist/optimization gates remain unchanged.
Native state evidence: .runtime/p0-05-native-approval-audit-1/installed-observation.json.

## P0-05 release metadata — expected NSIS payload hash verified (2026-10-26)

After closing installed recovery evidence, inspected the native EXE's raw hash discrepancy.
The restored build copy and installed copy differ at exactly3 bytes: Tauri's UNK bundle tag
becomes NSS inside the NSIS payload. Official pinned CLI2.12.4 source confirms patching and
post-bundle restoration. The manifest previously recorded only the restored build hash,
which is unsuitable for a direct installed-native comparison. This is a metadata gap, not
evidence of different application code or a reason to weaken raw artifact verification.

Updated scripts/release-manifest.py to preserve existing raw artifact hashes and separately
record expected_nsis_main_payload as a prediction for unsigned default NSIS patching. A
unique original/already-NSIS tag is required; missing/multiple/mixed markers, signed or
uncertain PE data and a missing inspector yield unavailable without a predicted hash.
Partial/failed bundles omit the expectation. The generator itself is now included in build
inputs. No executable bytes, signing settings, dependencies or user configuration change.

Six new positive/negative tests pass; combined release/discovery regression9/9 passes,
0 skipped,0.151s. Ruff passes for generator/application/tests. Actual complete and partial
CLI runs verify backwards-compatible raw hashes, absence of predictions for partial builds,
installation_verified=false, and the expected installed SHA902be457a388607067d3e28350ddb25095c5398bd07116fdb86d1a850ccedcf4.
That predicted hash exactly matches the real installed EXE. Source restored-build hash
remains42eb1c…; all3 raw artifact hashes and118 current manifest inputs still match.
The existing installer is unchanged and was not rebuilt for this metadata-only correction.
Source/evidence snapshots: .runtime/p0-05-nsis-payload-manifest/validation.json and after.zip.
P0-05 first/third remain open; metadata prediction is not clean-install/signature certification.

Owner subsequently confirms the installed window displays replies and that Copy and Stop
work. Record these as owner-verified native controls, separate from independent backend
generation/runtime evidence. Approval dialogs, native recovery/second-instance/shutdown,
physical capture/dialog/export and tested upgrade/history/uninstall still need acceptance.
Next native approval check requested in installed Agent: create only
native-approval-check/hello.txt containing NATIVE-APPROVAL-OK, deny the first creation
request, then resubmit and approve the fresh request. Target was absent before requesting
the check. No commands are requested; owner result is pending and is not counted as passed.

## Installed Ollama recovery — normal-session adoption/inference verified (2026-10-26)

Previous goal turn made progress implementing/testing/packaging the runtime-path correction.
Fresh read-only inspection now verifies the owner applied it: installed agent-backend.exe
matches SHA95ca89a8… and all62 local frozen modules match current source; installed agent.toml
contains the exact portable executable/models paths. Its original617-byte settings match
the exact saved backup (SHAf8b809a8…) and remain an unchanged prefix; parsed fields outside
[ollama] are unchanged. No owner configuration was modified by this audit.

The actual installed process tree is Explorer -> Studio -> PyInstaller backend parent/child
-> Ollama. One real model service lists qwen3.5:9b and qwen3-embedding:0.6b. This verifies
normal-session automatic startup without a separate model terminal; two backend image
processes are PyInstaller's parent/child, not proof of duplicate listening backends. A
content-free consistent read-only observation of installed state shows0 active tasks and a
completed reported chat with a1565-character reply,330 native generated tokens and1 model
call. Transcript text/prompts/credentials were not exported. Rendering/control operation
is not inferred from persisted backend data.

Previously blocked actual inference is now verified using that owner-started service:
the installed backend executable passes real Qwen browser navigation/screenshot1/1,15.521s,
and actual embedding/chat file import, restart/new-chat recall/citation, source-change
invalidation, reviewed reimport and whole-source forgetting1/1,8.935s. Both use disposable
fixture workspaces/authenticated APIs, not the owner's files or session credentials. The
original installed service remains running afterward. /api/ps records GPU-resident weights
for both models (qwen3.5:9b size_vram5,862,210,928/context8192; embedding1,228,857,671/
context4096). These are observed residency values, not a new latency/quality benchmark.

Direct read-only SQLite open could not create/use its journal machinery outside the managed
write scope. Instead, the observation required absent WAL/SHM, stable bounded main-file
identity/hash before/after reading and unchanged selected database, then queried a private
immutable copy. The first temporary copy's connection was not closed before deletion and
Windows refused its removal; the process exited, the exact owned file was removed, and
the corrected observer explicitly closes before cleanup. No private DB copy remains and
the original installed database was not written. These are point-in-time observations,
not a general live-backup facility or a guarantee that later user work remains idle.

A bounded read-only UIA probe still sees0 accessible native windows from this context.
Thus full native clipboard/dialog/capture/approval/cancel, second-instance/recovery,
clean standard-user installation, tested upgrade/history and uninstall data behavior
remain open. The owner was asked about visible reply/Copy/Stop. Managed owned-server
model-store access denial remains relevant to isolated cold trials, not to the now-working
normal Studio-owned service. No repeated corpus trial, source/default/security change or
new completion checkbox is justified by this recovery alone. Application behavior/installer
hashes remain the verified corrective build; fresh tests have0 skips. Evidence:
.runtime/p0-05-installed-ollama-recovery/validation.json and after.zip.

## Installed Ollama discovery correction — implementation verified (2026-10-26)

Updated installer:74,098,719 bytes,
SHA904b5a0010f258ce4acc2a57851e32c2f37df22777f066dbeef768de523103f7.
New sidecar SHA95ca89a8c363a940f1c58fc9f5a7b68844d4b7caf6a02a187761fe57cfcda44b;
release EXE SHA42eb1c0110ed168acfdcf404e575c9ed55bff66996573d04ddd62ae0b96b4f4a.
All117 current manifest inputs and artifact hashes match. The updated installer must be
applied in the normal Windows session, followed by the backed-up configuration helper.

Reproduced the owner's installed-app error. Portable Ollama exists at the repository's
.runtime/ollama/ollama.exe and models at .runtime/models, but installed agent.toml's base
is LocalAppData/local.agent.studio; PATH and standard Ollama installs are absent. The old
startup code searched only that base's portable path and PATH. setup-desktop.ps1 installs
Python/browser/frontend dependencies, not the model runtime. No download/reinstallation of
the existing models is needed to correct discovery.

Added trusted [ollama].executable/models resolution, standard Windows install fallbacks,
configuration-relative paths, actionable errors and strict invalid explicit-path refusal.
Existing running services are reused before resolution and never stopped/repointed; existing
development portable/store behavior and inherited standard model paths are preserved. Fixed
serve argv is host-owned, with no model/HTTP body override; endpoint validation prevents
invalid remote/public binding, and Studio launch credentials are removed from child env.
No tool permissions/default inference settings changed.

Added operator-only configure-installed-ollama.ps1/ollama_config: appends validated paths
to existing installed TOML with an exact backup, existing-byte/settings preservation,
atomic/DACL-preserving publication and conflicting-section/link refusal. No API/agent tool
exposes this maintenance operation. Actual installed configuration is outside this managed
workspace and was not modified here; the owner must run the helper in normal PowerShell
after installing the updated backend and closing Studio. Updated example comments and docs.

Verification:850 full tests,775 passed/75 skipped,352.958s;32 focused runtime/API/helper/
publication checks pass,5.698s; Ruff passes. Four helper tests were added after full-suite
discovery and are verified in focused checks, not retroactively counted in850. A new opt-in
real-runtime case is separately executed below. Initial import-order/unused-import lint
errors were corrected; no test guard was weakened. PowerShell helper syntax is checked.

New frozen backend has62 source-equal local modules, including ollama_runtime. Seven
fresh frozen real-startup/runtime/coding/MCP checks pass,0 skipped,30.857s. The new actual
test starts real portable Ollama via authenticated /models/start from installed-style
configuration, observes readiness, verifies owned shutdown/listener release and preserves
an unrelated process. Existing models are unreadable to that owned process in this managed
context (Access is denied; tags empty); this is recorded separately and is not a generation
pass. A separate owned metadata probe likewise starts Ollama0.40.7 and confirms that model-
store denial. Inference and the owner's installed UI require normal-session verification
after applying the fix; no native/upgrade acceptance checkbox is inferred.

Previous installer/backend/release/template artifacts were preserved. Updated NSIS installer
build succeeds with cached tools and the runner overlay (Rust18.19s). The existing large
frontend chunk/canonicalization warnings remain. No installed binary, user configuration,
service, model file or AGENTS.md was overwritten. New package hashes and remaining normal-
session apply/check steps are recorded in .runtime/p0-05-ollama-location-fix/validation.json
and after.zip. This corrective increment addresses discovery, with model-store access
explicitly distinguished from executable absence. Continuous goal resumes fresh from the
owner's instruction; no earlier blocked audit count is carried into this resumed work.

## P0-05 second increment — owner-built installer verified (2026-10-26)

The owner reports running setup-desktop.ps1, desktop-dev.ps1 and build-desktop.ps1
-ConfigLoaderRunner. Current artifacts independently confirm successful NSIS bundling:
dist/release-manifest.json created2026-10-27T00:14:29Z has bundle_succeeded=true and
installation_verified=false. All115 current source/config/lock inputs and all3 artifact
size/SHA records match; no source drift. The installer exists at
desktop/src-tauri/target/release/bundle/nsis/Local Agent Studio_0.1.0_x64-setup.exe,
77,019,958 bytes,SHA266fa4cf24a830cb4df08a7cd02ec5c60562f370e7cad3d8ab6cc360a35f66c7.
This resolves NSIS acquisition/build for this artifact; earlier managed10013 failures
remain historical and do not negate the owner's successful build.

New dist/agent-backend.exe is75,572,182 bytes,
SHA33d776b0bb9b5214701f900edc19d27987d14352aaa64a6b1793e4104df3f596;
all61 local frozen modules compare equal to current compiled source. Both deployed sidecar
copies exactly match it; release/resources/agent.toml matches the reviewed default template.
Release EXE SHA2ada6602f2e86d3a03df7d7ab783164c76303fbe2b4d8b1a1e9807bfec2486fb.
uv.lock and desktop/package-lock.json were retained unchanged by this verification;
uv.lock also matches B2a's saved hash. Offline lock check and npm dependency tree pass.
No application, dependency version, default configuration or AGENTS.md change was needed.

Verification against the new owner-built sidecar:17 frozen runtime/socket/coding/live-model
browser checks pass,0 skips,71.185s. This includes real Qwen browser navigation/screenshot,
approved external Python, counted unittest evidence, persistence after backend restart,
missing credential/config, authenticated sockets, port preservation and EOF shutdown.
Frozen real stdio MCP passes1/1,2.487s. Seven Rust tests pass,0 ignored, including concurrent
first-run complete configuration publication, existing config preservation, missing-template
cleanup, redacted diagnostics and native launcher startup-failure cleanup. An initial Rust
invocation redirected to an incorrect relative path and did not run; the corrected absolute
log invocation is the passing Rust evidence. No failed or skipped execution is counted as pass.

The generated NSIS script selects currentUser and packages the expected backend/resource
paths. Static uninstall source removes app data only when its delete-data checkbox is selected
and the operation is not an update. These are source observations, not an actual install/
uninstall/upgrade test. Installer payload was not independently extracted or installed here.
The original build script's reported full test/lint stage was not rerun or assigned invented
counts; the independently executed package/Rust checks above are the fresh evidence.

P0-05 second checkbox closes at its build/frozen-worker/browser/first-run-helper scope.
First and third remain open for actual native UI, single-instance/recovery, clean standard-
user install/upgrade and observed data retention. Asked whether the owner's development
window opened and answered a chat; no native pass is inferred from merely launching the
script. Next: close development Studio, run the built installer normally, and execute the
native checklist in docs/desktop.md. Existing user config/history must be preserved; use a
disposable coding project for tool tests. Evidence: .runtime/p0-05-owner-installer-verification/
artifacts.json, frozen.txt, frozen-mcp.txt, rust.txt, validation.json and after.zip.

## Remaining roadmap blocked audit3 — native/network prerequisites (2026-10-26)

Previous turn was progress: the current release candidate was built, archived and passed
six deployed-sidecar checks. This continuation re-read all authoritative project documents
and every unchecked roadmap item. The same underlying native/install prerequisites have
now recurred across three consecutive goal turns, with the safe independent memory and
release-refresh work completed in the preceding turns. No additional actionable increment
has satisfied dependencies; this is an external impasse, not roadmap completion.

At this preflight, existing Studio/Vite were absent, allowing the real owned diagnostic to
launch. It fails with native_startup_failure: WebView2 GPU exit0xc0000022/access denied and
gpu_unusable=true; no frontend request. This freshly reproduces the managed native failure
rather than merely refusing an occupied port. Owned process cleanup and raw-log removal
are verified. The owner's earlier successful normal-session preflight is a separate context;
neither observation verifies real app single-instance/recovery/install acceptance. Other
Studio/frontend processes reappeared during the audit and were left untouched. Report:
.runtime/native-diagnostic-ec1c59148b434b5eb86cdc3ee13aa61b/report.json.

Fresh pinned NSIS endpoint revalidation still fails URLError/errno13/winerror10013; no
dependency or installer was executed. NSIS is undiscovered in checked locations. Local
Ollama metadata still lists one completion-capable model plus the embedding-only model.
VM commands remain undiscovered; no approved provider/image is configured and host support
is unverified. The release-candidate SHA still matches its prior verified archive. Existing
negative specialist and optimization results remain rejected; no trial is rerun to obtain
a preferred outcome. Optional document/OCR work has no selected demonstrated input need.

All remaining boxes stay unchecked: P0-05 native/installer/standard-user upgrade; P1-07
supported VM isolation; P2-04 demonstrated specialist benefit; P2-05 second evaluated
completion candidate; optional P3-01 input need and P3-02 a qualified candidate/owned cold
admission. No application functionality, security default, user configuration or AGENTS.md
was modified. This audit ran diagnostics/dependency checks, not a new application regression;
the native observation failed and no blocked/skipped check is counted as passed.

Unblock steps: (1) use the normal unlocked Windows session to test the extracted current
release candidate against docs/desktop.md's native checklist; the managed GPU access
failure needs host-policy/runtime investigation if that execution context must be used;
(2) from an ordinarily permitted network run scripts/build-desktop.ps1 -ConfigLoaderRunner,
then verify installer hash and standard-user install/upgrade; (3) explicitly configure an
approved disposable VM and/or approve/install a second completion-model candidate if those
optional tracks are wanted. Keep security policy intact and do not stop unrelated services.
Audit evidence: .runtime/roadmap-gates/after-memory-blocked-audit-3/gates.json and
final-gates.json. Continuous execution is blocked pending an external-state change or
the required owner-session evidence; it is not marked complete.

## P0-05 partial release refresh — current memory UI/backend candidate (2026-10-26)

Previous goal turn made verified P1-03 progress. This turn reviewed all unchecked roadmap
items and found one safe packaging action despite installer/native gates: refresh the release
application with the now-qualified memory feature. Checked the installed Tauri CLI2.12.4
help and its exact upstream source. A fresh official NSIS3.13 download attempt fails before
receiving a package with URLError/errno13/winerror10013 (0.031s); no download was executed
or security setting changed. This changes the earlier historical-only download observation
into current dependency-blocker evidence. No NSIS/installer acceptance is claimed.

Preserved prior generated binaries in .runtime/roadmap-gates/after-memory-20261026/;
atomically copied the already source-equal B2a sidecar into the build input. The packaged
resource template exactly matched the reviewed example and was not modified. Tauri
`build --no-bundle --ci` with the documented temporary Vite runner overlay and offline Cargo
builds the current release EXE successfully (Rust26.33s). TypeScript/Vite assets exactly
match B2b's tested hashes. Existing chunk/canonicalization warnings remain. No application
source, dependency, user configuration or inference default changed.

Deployed target/release sidecar tests pass6/6,0 skipped,22.107s: actual runtime startup,
missing credential/configuration, EOF shutdown/listener release, occupied-port preservation,
authenticated socket snapshot and frozen approved external-Python coding/history. The sidecar
is byte-identical to B2a's verified61-module frozen backend. Candidate archive includes both
EXEs, the credential-free resources/agent.toml, manifest and honest acceptance instructions;
ZIP integrity and exact member readbacks pass. Native single-instance, recovery, install
and upgrade remain unverified, so all P0-05 checkboxes remain open.

Release EXE: desktop/src-tauri/target/release/local-agent-studio.exe,9,519,104 bytes,
SHA e898aec145df0039b662d876163a8c660f767adbc61c037bc0e468aa3b7aef0e.
Sidecar:72,564,239 bytes,SHA abe19526a339d05dd0aaab386c27088b691bde9c239dc74fcac983bce04f9744.
Archive: .runtime/roadmap-gates/after-memory-20261026/Local-Agent-Studio-0.1.0-release-candidate.zip,
74,875,587 bytes,SHA1410b6718195c69af7948b432d512ed558f9d0586836dd0eba56fbf302c3206b.
Evidence: release-validation.json, release-manifest.json, release-build.txt, release-smoke.txt
and nsis-acquisition.json in that same directory.

The user's debug Studio PID changed7552 to31716 during the build. Cause is not established
(development watching may restart changed artifacts); no explicit stop/kill was issued, and
Vite PID27352 remains. A stale-PID assertion initially failed, then fresh process inspection
identified the replacement; this was not treated as a failed application test or proof of
preserving the old PID. A bounded read-only existing-window UIA probe exits0 but observes
zero accessible windows in the managed context, no text/credentials exported; this is not
native readiness or proof the owner's window is absent. Existing native preflight refuses
to disturb Studio. Next: owner-session native checklist with Studio/Vite closed beforehand,
normal permitted-network installer build, then standard-user install/upgrade acceptance.
VM/model-routing/negative specialist-performance gates remain as documented; none is closed.

## Post-memory roadmap prerequisite recheck (2026-10-26)

P1-03 B2a/B2b/B3 and parent B are now verified at bounded explicit text-memory scope;
no remaining checkbox was closed by this prerequisite audit. A fresh native diagnostic
refuses to launch with reason existing_studio_preserved; native_launched=false and
native_acceptance=not_verified. The existing Vite PID27352/listener1420 and Studio are left
untouched. This run did not retest GPU initialization, so its empty GPU observations do
not resolve or reproduce the earlier managed-session0xc0000022 failure. The owner's prior
frontend_requested report is positive preflight evidence, still distinct from actual app
single-instance/recovery/install acceptance. Current report:
.runtime/native-diagnostic-c4457d2cb24346e18399362f7b97795c/report.json.

Fresh local metadata lists qwen3.5:9b with completion/vision/tools and qwen3-embedding:0.6b
with embedding, without completion. P2-05 still lacks a second evaluated completion
candidate; embedding installation does not satisfy that prerequisite. VBoxManage/vmrun
are undiscovered on PATH and earlier PowerShell Get-VM lookup returns none; VM host support
remains unverified, with no configured disposable provider/image. NSIS is undiscovered on
PATH, the two checked Tauri cache locations and Program Files. Historical download10013
remains historical; this audit did not retry acquisition or claim a current DNS failure.
Metadata probe initially used two incorrect wrapper assumptions (base_url/close); corrected
to the actual url/request context-manager API without application changes.

Next actionable release work: close Studio and its Vite frontend in the normal session,
then perform P0-05 actual native UI/single-instance/recovery/shutdown acceptance as documented
in docs/desktop.md. Acquire/build the NSIS installer using the ordinary build script and
verify standard-user install/upgrade separately. VM isolation requires an explicitly
configured supported provider/image; routing requires a second measured completion model.
Do not bypass permissions, kill unrelated processes, adopt failed specialist/performance
candidates, or add optional OCR/document features without a demonstrated input need.
Current gate inventory: .runtime/p1-03-memory-acceptance/remaining-gates.json.

## P1-03 B3 — combined memory qualification verified (2026-10-26)

Added opt-in tests/test_memory_acceptance.py using the immutable v1 corpus (SHA2108b57f…,
32 unchanged notes,32 literal and32 paraphrase questions). Before running, fixed the source
arrangement:16 explicitly imported files,2 exact900-character chunks/file with whitespace-only
padding;64 same-project distractors and32 matching notes in another project. Production
MemoryIndex.reindex/search runs with the actual installed embedding model, after Manager
restart and explicit enable. Predeclared gates remain >=90% paraphrase recall@5, no literal
loss, >=10 percentage-point paraphrase gain and zero cross-project results. No corpus edits,
query retries or selection of best results. The same run checks real chat citation/provenance,
source-change/vector/history exclusion, whole-source forgetting and source-chat deletion,
preserving original files and other-project memory. A content-free report is written even
on failure; completed retrieval observations cannot be promoted from an incomplete run.
Application/backend/frontend behavior and packages are unchanged from B2a/B2b.

The single actual production run passes1/1,43.984s: literal hybrid32/32 versus keyword32/32;
paraphrase hybrid30/32 (93.75%) versus keyword14/32 (43.75%), a50 percentage-point gain,
with zero cross-project results across64 queries. Zephyr and Acorn remain the two misses;
the fixed corpus and model/query configuration were not tuned or retried. Model identity:
qwen3-embedding:0.6b/ac6da0df…/1024 dimensions/Ollama0.40.7. The same run passed actual
chat answer/parent citation/source hash/spans, stale admission refusal before task creation,
changed-source vector removal and old model-history exclusion, confirmed whole-source forget,
and source-chat cascade while preserving other-project notes and original files. Its report
is .runtime/memory-acceptance/28c9abc479d44c1b87020ae90985e74e/report.json.

Focused contracts:89 tests,83 passed/6 opt-in skipped,26.119s; Ruff passes. Existing source/
frozen actual-model workflows and B2b rendered source/frozen review tests are reused because
application sources are unchanged. Full default836/765 passed/71 skipped remains B2a's
application regression evidence; no new full-run claim is made. New automated live acceptance
is separately opt-in and its ordinary discovery skip is not a pass. UI/browser IPC fixtures
do not verify native packaging. B3 and P1-03 B close at bounded explicit text-file/note memory
scope. Evidence/source snapshot: .runtime/p1-03-memory-acceptance/validation.json and after.zip.
Remaining roadmap gates require native/installer access, a supported VM provider or another
qualified completion model; earlier negative specialist/performance trials remain unapplied.

## P1-03 B2b — file-source controls verified (2026-10-26)

Added FileMemoryControls inside Project memory, reusing the existing approved project chooser
and authenticated B2a API. Users select an exact project-relative UTF-8 path, review raw
hash/version and every excerpt/span, then explicitly confirm import/replacement. Saved-source
metadata is labelled; Check sources observes freshness and stale state. Reimport always
requests a fresh preview. Whole-source forgetting confirms removal of every excerpt/vector
while preserving original files and visible transcripts. Network operations close modals to
leave Emergency stop available; busy controls prevent conflicting memory operations.
Generation/scope/conversation guards discard late previews and metadata across navigation.

Initial rendered review/import/conflict/reimport/forget and delayed-preview cases pass2/2,
6.487s. Focused memory/index/admission/discovery checks pass72/76,4 opt-in skips,21.035s.
23 frontend utility tests pass,149.044ms. TypeScript/Vite runner build and Ruff pass; ordinary
bundled-config build hits managed parent-directory access denial, so the existing documented
configLoader runner option is used without changing permissions. Existing chunk warning
remains. Frozen-backend rendered acceptance passes3/3,13.942s, including blank-conversation
creation, keyboard/900px review and delayed old-project metadata. Two test assertions were
corrected (ambiguous conversation/navigation title and canonical relative project label);
earlier failures are retained. Final source blank-conversation/legacy memory/semantic/keyboard
UI regression passes4/4,18.384s. Every new scenario is verified against the unchanged frozen
backend. B2b is checked; documentation/evidence is closed at
.runtime/p1-03-memory-source-ui/validation.json and after.zip. The836-case full default run
belongs to B2a; it was not repeated for this frontend-only increment. Current focused checks,
Ruff, utility tests, build and rendered regressions provide the relevant verification.
Backend Python/schema/dependencies are unchanged from verified B2a; the same source-matching
frozen backend is reused. Native WebView2/installer acceptance remains unverified. Next is
B3 combined production retrieval qualification and lifecycle/security acceptance.

## P1-03 B2a — file-source backend verified (2026-10-26)

Implemented and verified: schema v10 source/chunk provenance and cleanup/stale
triggers; memory_sources.py bounded confirmed UTF-8 preview/import, raw hashes/resource
versions, normalized BOM/newline view and character/line spans. Reimport checks the exact
preview and prior source generation, replaces derived data transactionally and never writes
original files. Whole-input credential/control checks precede chunking. Source checks reuse
Coding.read/fingerprint outside the cancellation lock, validate saved chunk layout/text/hash
against observed file data, and reject stale receipts before context admission. Changed,
missing, unsafe or inconsistent sources become stale, lose vectors and advance the memory
history epoch. Keyword/hybrid recall excludes stale chunks; visible snapshots remain.

Memory/semantic/task-admission paths now carry host-owned source receipts. Read-only APIs
can inspect saved excerpts during active tasks without file I/O, but cached receipts cannot
admit model context. Added authenticated strict source routes, whole-source forgetting and
file provenance/forgetting labels in MemoryPanel. Retention reviews include source/chunk/
vector rows and refuse cross-conversation links; populated backup/restore fixtures and
legacy migration expectations were extended rather than weakening assertions.

Early verification:56 legacy memory/index/admission/migration tests,53 passed/3 skipped;
53 first source/backup/restore/retention checks pass. Broader focused222 tests,219 passed/
3 skipped,83.961s; Ruff and TypeScript/Vite build pass. A new worker test initially inspected
the execution-prompt message rather than the earlier user memory message; corrected to
inspect actual quoted user data. Two added retention tests used the wrong method name;
corrected to the existing apply interface. Failed logs are retained. An admission-order
issue was fixed: source invalidation now precedes model/vision admission, so an obsolete
image in excluded history cannot incorrectly block a text-only model. A real valid PNG
API regression covers the ordering;91 admission checks pass,88 passed/3 skipped.

Final default regression:836 tests,765 passed/71 skipped,340.462s. The final source-only
checks pass25/25 before the additional API ordering case; the latter passes separately and
is included in full discovery.23 frontend utility tests pass,134.677ms. Ruff, offline lock
consistency and TypeScript/Vite build pass; the existing chunk-size warning remains, with
no dedicated frontend linter configured. Actual local embedding/chat source workflow passes
1/1,6.851s: confirmed file import, restart/new-chat exact recall/citation, changed-source
invalidation and stale admission refusal. The rebuilt frozen backend passes real API/model
import/restart/recall/source-hash/change/reimport/whole-source forgetting,1/1,13.533s.

Rendered source file provenance/stale listing/confirmed forgetting passes1/1,2.939s.
The frozen regression command runs5 cases:4 pass (file provenance, semantic controls,
backup and approved external-Python coding),1 restore-UI error before its scenario because
the user's Vite process owns localhost1420. That process is left untouched. The error is
not a pass; populated backup/restore storage coverage passes in the focused/default suites.
Rendered checks use browser IPC/protocol inference fixtures and do not establish native
WebView2 or actual-model quality. Actual-model evidence is separate above.

Wheel:73 source-equal modules/exact corpus/isolated schema10 import pass,
SHA ccb53f3bfe09e510cf992bfa46c7ccc9a24b77b59a1ea73ad4280640ad7b6434.
Frozen .runtime/p1-03-memory-sources/dist/agent-backend.exe:61 source-equal local modules,
72,564,239 bytes,SHA abe19526a339d05dd0aaab386c27088b691bde9c239dc74fcac983bce04f9744.
B2a acceptance is satisfied and its checkbox closes. B2b source-selection/review controls
are next; B3 combined acceptance and native/installer/VM/routing gates remain open.
Evidence/checklist/source archive: .runtime/p1-03-memory-sources/validation.json and after.zip.

## P1-03 B1b ? optional hybrid Studio context verified (2026-10-26)

B1b is complete at saved-note scope. Added per-project confirmed enable/disable bound to
an exact index generation in existing metadata; indexing keeps/selects the original keyword
path. Fresh model validation, semantic query and source collection occur outside the host
cancellation lock. memory_admission.py validates conversation/history/effective regeneration
objective, scope/forget epoch/index generation and setting before creating a task; source
IDs resolve again from current scoped notes. Existing quoted-memory framing, excerpts,
parent citations, fresh approvals and tool-profile boundaries remain intact. Test/diff/
selected-file inspections skip embeddings; disabled projects retain keyword behavior.

SemanticMemoryControls/MemoryPanel add installed-model selection, index and enable
confirmations, related-wording/keyword context, independent semantic search, honest local
status and stale-response guards. Reindexing selects keywords until explicitly re-enabled.
Confirmations close on request start so global Emergency stop remains accessible; cancellation
uses owned HTTP clients and preserves prior indexes/settings. Stale enabled indexes block
admission instead of silently falling back. No user config/default model or dependency changed.

Verification:808 default tests,739 passed/69 skipped,334.923s;159 focused,155 passed/4 skipped,
70.445s;23 frontend utility tests,0 skipped,133.998ms; TypeScript/Vite builds pass with the
existing large-chunk warning. No dedicated frontend linter is configured; Ruff passes for
Python. Offline lock consistency passes. New real-worker/API cases preserve quoted context,
parent citations, regeneration plan mode, stop availability and fresh denied write approval.
Actual embedding/chat models recalled an exact saved identifier after Manager/conversation
restart, then forget removed vector/model history and stale admission (1 pass,6.658s).
The rebuilt frozen API repeated that workflow with a distinct identifier, real backend
restart, source citation and explicit keyword selection (1 pass,11.605s).

Rendered source semantic controls pass (1,4.814s): index/enable cancellation and confirmation,
model selection, scoped inputs, real hybrid API search, quoted worker request/citation,
keyword selection, emergency interruption and stale old-scope response rejection. Four
legacy memory/slash/keyboard/backup UI checks pass,16.721s. Against the new frozen backend,
the semantic UI, legacy memory UI and approved external-Python workflow pass (3,14.969s).
Rendered tests explicitly use a browser IPC bridge and protocol inference; they are not
native-window or actual-model quality evidence. Actual-model API tests are separate above.

Initial new tests selected a wrong fixture call and raced an unfinished semantic search;
fixed assertions wait for actual request completion and inspect its input. React StrictMode
created two held old-scope status requests, so the stale-response test now fulfills/checks
all captured old responses rather than assuming one. Failures remain in evidence; no
scope/approval guard was weakened, quality corpus changed or skipped case counted as pass.
A first lint invocation used the desktop cwd and failed to find Python Ruff; the later root
invocation passes. All current application/test changes are included in the final checks.

Wheel has72 source-equal modules plus exact corpus and a passing isolated import,
SHAda5ba37c61ffa7a2615bcd9db4d9452b6cb56a49ec33a7b7b94f105ede182ed1.
Frozen .runtime/p1-03-memory-integration/dist/agent-backend.exe has60 source-equal local
modules,72,549,201 bytes, SHA747cd8e744ee8778bc8692b7a3c502da471d02e4fd9aee6a0836c576719c9dac.
Evidence: .runtime/p1-03-memory-integration/validation.json and after.zip. Updated README,
project-memory guide, architecture/gap review and ROADMAP. B1b is checked; full B remains
open. Next: B2 explicit approved text-file chunks, source spans/hashes/version tracking and
changed-file invalidation, followed by B3 combined acceptance. Native/installer/VM/routing
and earlier negative performance/specialist gates remain unchanged; the full goal is active.

## P1-03 B1a ? explicit persisted note index (2026-10-26)

B0's actual retrieval benefit made this increment actionable. Added SQLite v9 derived
note indexes/vectors, checksums, normalized float32 encoding, exact note hashes,
model/digest/server/dimension/query-format identity, manifest/forget epoch and exclusive
generation. Composite note/scope foreign keys enforce ownership; forget/source-chat
removal cascades vector rows immediately. Confirmed reindexing replaces metadata/vectors
in one transaction; failed inference, SQL publication faults, concurrent notes/project/
generation changes or host cancellation preserve prior published state. Model changes
require reindex before query text is sent; results revalidate their source snapshot.

New authenticated/origin-protected /memory/index GET/POST and /memory/hybrid GET routes
operate only on explicitly saved notes in one current approved project. No endpoint
accepts commands, filesystem inputs or an alternate inference URL. Exact session secrets
and recognized credentials are excluded. Status clearly marks live model identity as
not checked. Shared retrieval.py preserves B0's exact scope-filter/cosine/RRF algorithm.
No new dependency/framework, file crawl, user configuration edit, chat-model change or
automatic prompt/UI behavior was introduced. B1b and file chunks B2 remain incomplete.

One host-owned embedding lease prevents duplicate operations and task admission while
inference is active; network calls stay outside Manager.lock. Emergency close remains
available and aborts publication. Initial new cancellation tests failed: Windows buffered
recv remained blocked after owned socket shutdown. A first repeated-shutdown attempt
also failed and was not accepted. The final owned duplicate socket uses bounded
nonblocking reads with cancellation/deadline polling, while retaining the standard HTTP
parser. Both owned handles are closed; no shared Ollama/Python process is killed. All20
repeated cancellation checks now pass. Initial migration/backup fixture failures were
corrected by preserving strict expected schema history and seeding actual vector rows;
backup/restore assertions were retained, not weakened.

Verification: final790-case default regression,723 passed/67 skipped,349.059s; focused164,
161 passed/3 skipped,72.653s. A SQL-trigger publication-fault test was added after that
discovery snapshot and passed separately (1 test,0.080s); runtime sources did not change
then. The current default suite therefore has one additional test for the next full run.
Actual local source embedding/index contracts2 passed,2.276s. Actual frozen HTTP API
index/restart/paraphrase/source/forget workflow1 passed,7.423s; existing frozen approved
external-Python test1 passed,6.332s. The first frozen attempt was refused before execution
by the idle guard; a fresh read-only state check found no active task and the retry passed.
No unrelated task was cancelled. No skipped case is counted as passed.

Ruff and offline lock checks pass. Final wheel contains71 source-equal modules and exact
packaged corpus, with a passing isolated import. Final frozen sidecar contains59
source-equal local modules, including all changed production modules; actual APIs were
exercised in that executable. Wheel SHA b2b01dbd20a250b4d93d1425214357e14353b8db4bdf640efb514646f034c993.
Binary .runtime/p1-03-note-index/dist-final/agent-backend.exe,
SHA98f00e88ab2841102fac078fe5779b794f6ffb39cf5258fa0c8c73832f46afd5,
72,542,218 bytes. The earlier pre-cancellation-fix binary is historical, not the accepted
artifact. Native frontend/installer gates were not rerun or claimed by this backend test.

Files: embeddings.py, retrieval.py, semantic_evaluation.py, studio/memory_index.py,
manager.py, api.py, migrations.py; embedding/index tests and migration/history/schedule/
watch/backup-restore fixtures. Updated memory/backup/architecture/gap/roadmap docs.
Evidence .runtime/p1-03-note-index/validation.json and after.zip retain failed and final
logs plus the reproducible owned frozen acceptance script. B1a is complete. Next B1b:
index controls and explicitly enabled prompt retrieval, with preflight outside the host
lock and final snapshot validation. B2 source files/chunks and B3 integrated acceptance
remain open. The full roadmap goal is still active and incomplete.

## P1-03 B0 ? evaluated local embeddings (2026-10-26)

The previous turn made progress by installing/observing the new embedding dependency
and completing the first fixed real retrieval study. B0 is now verified. Existing
production generation, scopes, memory behavior and user configuration are unchanged.

Added embeddings.py: direct local-only HTTP, no proxy/redirect/truncation,16-item/8KiB
input limits,2MiB response cap,30s absolute request budget, finite normalized vectors,
installed model/digest/server/dimension validation before and after each batch. Model
changes discard results; native counters and content-free receipts stay bounded. Strict
boolean/nonfinite timeout/dimension checks and huge integer guards reject malformed data
without leaking server messages. No new framework/dependency or shared-process restart.

Added semantic_evaluation.py and immutable packaged memory_recall_corpus_v1.json.
The actual study uses real isolated SQLite lexical search and scoped cosine/RRF results:
32/32 literal retained; paraphrase30/32 hybrid (93.75%) versus14/32 lexical (43.75%);
zero cross-project results among96 scoped/32 excluded documents. The predeclared gate
was no literal loss,90% paraphrase recall,10 percentage points improvement and no scope
leaks. Zephyr and Acorn remain misses. There was one actual quality run, no corpus
retuning or result-selecting retries. Twelve batches/192 inputs used15.416s measured
embed wall time and3207 native prompt tokens; these are not generation token/s metrics.
Model digest ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d,
1024 dimensions, Ollama0.40.7. Exact trial sources/report are archived before later
validation-only changes. Future reports include source hashes; protocol fixtures cannot
claim a quality pass. No production index or broad retrieval quality claim yet.

Verification: full773 tests,707 passed/66 skipped,330.917s; focused53/50 passed/3 skipped,
26.282s; separate actual local embedding contract1 passed,1.447s. An initial new baseline
fixture test used a wrong key, fixed without changing corpus/application behavior; its
failure log remains. After the full run, an oversized-integer guard was hardened; final
embedding/evaluation checks15 passed/1 opt-in skip,8.215s. Existing67 runtime modules
remain unchanged. Ruff and lock checks pass; final wheel has69 source-equal Python
modules, the exact corpus and a passing isolated import. No skipped test is counted as
passed. No frozen/UI checks are claimed for this development-only prerequisite.

Evidence: .runtime/p1-03-embedding-evaluation/validation.json and after.zip; actual study
.runtime/semantic-evaluations/3981d732a414477b99ebbd0a752cc048/report.json. Updated
ROADMAP/architecture/gap/project-memory documentation. B0 is complete; full B remains
open. Next: B1a persisted scoped note index and authenticated explicit reindex/search,
then B1b prompt/UI integration, B2 approved file chunks, B3 real integrated acceptance.

The owner native report33db10a872974073abeac90c334a56a5 reaches the harmless frontend
without observed GPU errors and closes only its owned process. Managed-session failures
are retained. This is preflight evidence only; native React/IPC/installer acceptance is
still unverified. The previous prerequisite audit below is historical, not current model
availability: the owner has now resolved embedding acquisition in an ordinary session.

## Remaining prerequisite audit and recovery-guide correction (2026-10-26)

The previous goal turn made implementation progress: the native diagnostic prerequisite
was completed and verified. This continuation finds unchanged external prerequisites,
with no new capability implementation or test pass claimed.

Fresh checks: primary Ollama still lists only qwen3.5:9b; registry DNS resolves, but
ordinary registry/GitHub/PyPI HTTPS connections fail Windows10013. MCP and mcp-types2.3.0
are installed and the documented require_sdk check passes. The managed thread desktop
remains CodexSandboxDesktop-8d5e769594f5f2a6dfce965abe2d477b; no Studio test process or
live owned handle remains. NSIS and an installer artifact were not found. No new VM,
routing candidate, ingestion need or passing specialist/optimization gate appeared.

Corrected obsolete SDK-missing statements in docs/recovery.md and ROADMAP.md's current
blocker overview. Updated docs/project-memory.md to reuse scripts/pull-model.ps1 with
the documented embedding tag from a normal authorized session. The old private helper
was not a shipped setup command and rerunning it in place overwrites acquisition.json;
its original evidence remains intact. Embedding availability alone does not satisfy
semantic acceptance or the second chat/tool routing prerequisite. No managed request
to the primary service's pull endpoint was made as an egress workaround.

Verification: the pinned SDK check passes; documented PowerShell fences parse. The model
download snippet was syntax-checked only, not executed or counted as an installation.
All156 Python source/test files match the previous verified snapshot, so no application
tests, build or native failure probe were repeated. Prior757/692 passed/65 skipped
retains its original scope; it is not a fresh test run. Evidence:
.runtime/roadmap-gates/after-native-diag-audit-1/validation.json.

Normal-session native diagnostic status and ordinary embedding-pull results were requested
as asynchronous missing information. They are pending, not inferred from elapsed time.
No roadmap checkbox was closed. Native/installer/VM and dependency/benefit requirements
remain open; the full goal is incomplete.

## P0-05 native diagnostic prerequisite verified (2026-10-26)

Continued after P2-02 and investigated the previously inconclusive native startup.
Win32 inspection finds the actual owned Tauri window and WebView2 children on the
managed desktop. A scoped PrintWindow capture succeeds and shows a blank white window.
WebView2 logs localize the failure: GPU subprocesses repeatedly exit-1073741790
(0xc0000022/STATUS_ACCESS_DENIED), then report GPU unusable. The specific underlying
access operation is not identified. Existing registry/DPAPI warnings are not treated as
proof of that cause. A temporary owned --disable-gpu troubleshooting run also fails;
an isolated profile in the approved standard OS temporary directory fails with the
same code, so the failure is not resolved by changing the profile location either.
Normal rendering, inference settings and security controls remain unchanged.

Added local_agent/native_diagnostics.py, tests/test_native_diagnostics.py and
docs/native-diagnostics.md, with README/desktop guidance. This development-only check
is not an agent tool or privileged HTTP API. It launches only the checkout's debug
executable, refuses existing Studio/backend or an occupied frontend port, and uses
an exclusive workspace profile with a harmless, script-free localhost1420 page.
It never calls backend_connection or submits tasks. Observation is1–30s; a hard
per-connection deadline prevents dripping HTTP headers from stranding shutdown.

The helper reuses ProcessOutput/Windows Job cleanup and preserves caller environment
settings, adding only per-process profile/logging options. Reports are under8192 bytes
and contain fixed categories, bounded codes and timing/PID metadata, no raw logs,
stdout, paths from logs, URLs or credentials. Log capture stops at an observed1MiB
threshold; reads are capped and truncation is explicit. Identity/link checks protect
log read/removal; profiles, unknown files and unsafe/replaced logs remain intact.
`native_acceptance` always remains `not_verified`, including a requested test page.

Verification:

- Final default757:692 passed/65 skipped,327.244s. No failed tests. Skips remain explicit.
- Focused13:13 passed,12.606s, including the opt-in actual native diagnostic. Its report
  is .runtime/native-diagnostic-3d21c91032234058aa78a18c7dbb9151/report.json and explicitly
  records observed_failure, GPU access denial/unusable, raw log removed and owned closed.
  This validates diagnostics/cleanup; the native application failed its startup probe.
- Real fixture process-tree deadline test confirms an unrelated owned test fixture
  survives; private stdout/log values never enter the report, unknown files remain,
  and only the captured log is removed. Real HTTP tests cover path/method restrictions
  and absolute shutdown deadlines under continuously dripping headers.
- Initial test-fixture quoting error was corrected before final checks; its failing
  targeted-second.txt is retained. No failed/skip result is relabelled as a pass.
- Documented CLI ran against the actual executable: exit1 as expected for observed
  startup failure. It produced .runtime/native-diagnostic-94e098bf1ed9448a82b0dd25c5babaf4/
  report.json; no application-acceptance claim is made from that command.
- Ruff and offline lock check pass. Wheel67 Python entries match current source;
  independent unpacked-wheel import/classification passes. Wheel SHA256
  0521ce62c873a5a18db6986d55b2919a91031a92d2a3d9e74ed427215cf5b995.
- All66 prior runtime Python modules match the closed P2-02 hashes. No production
  native/Rust/frontend/agent module changed; no new frozen binary or installer is
  claimed. Prior runtime/frozen checks retain their original, unchanged-code scope.

Evidence: .runtime/p0-05-native-diagnostics/validation.json and after.zip. The roadmap
checks only this diagnostic prerequisite; P0-05 native/single-instance/crash/recovery,
installer and upgrade requirements remain open. See docs/native-diagnostics.md for
normal-session retry and evidence collection. Next required work is native acceptance
after resolving this GPU-subprocess failure, or P1-03 B after embedding acquisition.
Embedding registry10013, absent NSIS/VM setup, one routing model and the prior failed
specialist/optimization benefit gates remain unchanged. No unsafe GPU/sandbox flag,
desktop reassignment, administrative request or unrelated-process termination occurred.

## Remaining-gate recheck after P2-02 (2026-10-26)

The MCP increment below is closed and verified; its archive/hash boundary is preserved.
Continued with independent gates without modifying application functionality further.

- P1-03 B: primary Ollama still lists only qwen3.5:9b. Copied the reviewed acquisition
  helper into a fresh workspace cache and ran it with an owned supervisor. Its private
  Ollama became ready, then registry.ollama.ai resolved104.18.17.170 but connect failed
  with10013. Acquisition exit1, no embedding model, watchdog not expired; owned helper
  and server closed. Evidence: .runtime/p1-03-after-mcp-1cd4cca183514fcab87d08b36e74f6a6/.
- P0-05: input-desktop read/create-window/write-object handle requests now succeed.
  A separate bounded UI Automation import/initialization/own-process enumeration probe
  passes. These checks do not establish native Studio readiness. With no existing
  Studio, an owned native preflight stays alive; accessibility lookup stalls and is
  stopped by the supervisor. Ownership was checked by exact executable, parent,
  creation time and unique WebView profile before cleanup; no owned PID remains.
  A second bounded bootstrap with an owned localhost1420 fixture receives no requests
  within12 seconds. No IPC/UI pass is claimed. The managed process thread desktop is
  CodexSandboxDesktop-8d5e769594f5f2a6dfce965abe2d477b, while input desktop is Default.
  This identifies the execution context; the exact native startup stall is undiagnosed.
  No desktop reassignment, security change, user-profile deletion or native config
  override was introduced. A config override would not address the observed pre-frontend
  gate, so the proposed test-isolation change was deferred.
- No NSIS installer exists and provider commands were not found on the current PATH;
  this is not proof that virtualization is unavailable. No new model-routing candidate
  or demonstrated document-ingestion need appeared. Existing failed specialist and
  optimization benefit gates remain unchanged.

Evidence: .runtime/roadmap-gates/after-mcp-20261026/gates.json references the separate
native probes. Native/installer/VM and semantic retrieval requirements remain unchecked.
Ports1420/17861 are free, no Studio test process remains, and primary Ollama still serves
the existing model. Further native acceptance needs a normal interactive Windows session;
embedding work needs ordinary permitted model acquisition. Documentation-only recheck
does not rerun or overwrite the closed MCP evidence writer or count skips as passes.

## P2-02 — Read-only local MCP provider verified (2026-10-26)

The user-acquired isolated SDK now imports as2.3.0. Inspected its actual v2 session,
server, stdio and Windows process behavior and the existing Policy/ToolSpec/worker/
journal/observability boundaries. Reused the official SDK instead of adding another
agent framework. Installed16 missing packages from the SDK cache; no existing
application dependency version was upgraded. Ordinary online resolution still fails
10013; no network/security policy or production process-environment filter changed.

Implemented opt-in `mcp_project_read` for coding/unified profiles, backed by one shipped
read-only version1 server. SDK/client/type packages are pinned2.3.0. Commands, URLs,
environment and provider registration are not model inputs. The host and server both
enforce approved scope, strict links/credential/dependency/state exclusions and stable
file identity/hash checks. Reads are UTF-8,8192 bytes maximum; redaction precedes the
stdio result and model/durable events. Catalog/description/identity changes fail with
MCPReviewRequired. Only reviewed responses are accepted; SDK sampling/root/elicitation
requests have no execution authority. No privileged HTTP endpoint was introduced.

The custom bounded pipe transport wraps the official session API because the default
SDK stdio reader has no unterminated-line byte cap. Frames65536 bytes, total traffic
131072 bytes, requests4096 bytes and a1–30s trusted deadline are enforced. Windows
processes start suspended, join an owned Job, then resume; stop, timeout, close and
failure clean only that tree. SDK and transport errors use fixed safe messages.
Fresh server per call means no reconnection, approvals or side effects are replayed.

Files: new mcp_contract.py/mcp_process.py/mcp_provider.py/mcp_server.py; Tools registration,
observability allowlist, journal read classification and frozen-runtime dispatch; optional
dependency/lock and desktop setup/build wiring; MCP fixtures/tests and observability
regression; docs/mcp.md plus repository status documents. Existing agent.toml and UI
sources are unchanged. Enable the optional trusted section as documented, then restart
source Studio. Older installed executables require rebuilding; this is not new installer
or installed-app acceptance.

Verification:

- Final default suite744:680 passed/64 skipped,318.045s. Initial742-case run retained
  one observability test failure: it assumed the default registry contained every optional
  tool. Updated positive disabled/enabled assertions; no tool authorization was relaxed.
- Focused MCP17:15 passed/2 opt-in skips,16.738s. Real handshake/list/call, approvals/
  profile boundaries, direct server denials, malformed/oversized/partial/disconnected
  peers, schema changes, timeouts, cancellation, unrelated-process survival, secret-env
  filtering, failed Job/resume and actual Studio worker/journal persistence are covered.
  The first12-case run had two immediate PID-existence assertion failures; both processes
  were gone on subsequent inspection. Bounded termination assertions cover asynchronous
  Windows reaping. Suspended startup also prevents children escaping pre-Job assignment.
- Actual Qwen3.5:9b Studio task used the real MCP provider successfully. Its opt-in
  case passed; this is functional acceptance, not a quality/performance benchmark.
- Actual frozen MCP stdio and existing frozen approved external-Python test/history
  workflow:2 passed,7.068s. An initial test incorrectly marked its source host as frozen,
  breaking pywin32 imports; fixed the fixture to launch the real frozen command instead.
-54 targeted registry/journal/observability cases:53 passed/1 live skip,19.431s.
- Post-sync MCP/observability regression:32 passed/2 opt-in skips,20.674s.
  Ruff passes. Wheel66 Python entries match current source; isolated unpacked-wheel
  import and real stdio read pass. Wheel SHA256
  39f60644e854a6463951c5fb96f31a8c45ef4a5be85b4003de1a330f69e0f487.
- Frozen backend built after excluding optional MCP development-CLI collection, which
  initially required absent typer. Runtime SDK modules/metadata are collected explicitly.
  Backend SHA2569bdee40cd16d63f87887177ee26cd30513bc395ca0aee18e0a5685ea462c2628.
- `uv lock --check --offline`, locked offline dependency sync and compatibility check
  pass. The lock targets the Windows/Python3.12 setup runtime. `uv.toml` carries29 exact
  version-specific dependency metadata records copied from the isolated SDK wheels,
  including extras/markers; dependency-proof.json checks all fields against that source.
  These records only apply to matching versions; the working application retains
  Starlette1.9.0 while an unused probe metadata entry describes1.10.0. No requirements
  are relaxed. Other platforms/Python runtimes need separate resolution/verification.
  Refresh/remove these records when upgrading packages with normal network access.

Evidence and preserved failed attempts: .runtime/p2-02-mcp-integration/validation.json
and its referenced logs/proofs/archive. No other roadmap checkbox is completed.
Remaining limits: no arbitrary MCP executable/URL, remote transport, provider mutations,
OS sandbox or new installed Windows acceptance. First increment acceptance is satisfied.
Next independent priority is P1-03 B embedding evaluation; the service still lists only
qwen3.5:9b, and ordinary registry acquisition remains externally blocked10013. Existing
native installer/VM, multi-model routing and failed cold/per-case performance gates
remain open. No model/default change or unrelated process termination was performed.

## Dependency recovery instructions verified against host documentation (2026-10-26)

The resumed environment still has no MCP SDK/probe Python, embedding manifest or NSIS
artifact, and lists only the existing Qwen model. A fresh ordinary SDK dry-run again
fails2 with PyPI10013; no probe environment/install was created. Evidence:
.runtime/roadmap-gates/resume-6bd2b4d424634c04aa96ca11bd4a271d/mcp-online.txt.

Used the OpenAI Docs skill and fetched current official Windows sandbox, permissions
and network-control documentation. Command networking and hosted search are separate;
resuming the goal does not change the effective policy. No client configuration or
host firewall/ACL/account setting was modified. docs/recovery.md now explains that
boundary and the owner-approved/narrow-network route, plus ordinary-session setup.
The SDK snippet preserves existing partial directories, checks command failures and
verifies the pinned import. Its syntax is checked separately; no download, SDK runtime
compatibility or provider acceptance is inferred. Application/test sources and the
closed live trial/default decision remain unchanged. P1-03 B/P2-02 stay unchecked.

## Independent dependency retry after A1b1 (blocked acquisition, 2026-10-26)

The complete actual comparison is closed below, with its failed adoption gate retained.
The next higher-priority independent candidates still need external dependencies:
MCP2.3.0 is absent; fresh isolated-cache dry-runs exit1 offline and2 online with PyPI
socket10013. No dependency is installed into the application environment.

The official Qwen3 embedding0.6b candidate remains available in the catalog (639MB).
Disk headroom exceeds470GB; no proxy environment is present. Reused the documented
acquisition helper in new sibling workspace directories, preserving old caches/evidence.
The first supervisor wrapper removed USERPROFILE and failed before readiness. That
setup mistake is retained at .runtime/p1-03-acquire-bcc06818d77f4f8586dcd3b2ac10e54a/.
Corrected only the trusted setup launcher to use its ordinary Windows environment,
an owned ProcessOutput job and240s watchdog. Production command filtering is unchanged.

The corrected attempt .runtime/p1-03-acquire-1137022484f844a38fb4364ca4db44e8/ reaches
its private Ollama API, then fails registry HTTPS with connectex10013 after DNS resolves.
No embedding model is acquired. Its server closes and no owned port listener remains;
the unrelated primary service still runs and lists only qwen3.5:9b. No primary download
proxy, alternate transport, credential/ACL/firewall change or model inference was used.

Current observations/logs: .runtime/roadmap-gates/after-live-20261026/gates.json,
mcp-*.txt, embedding-retry.txt and embedding-trusted-retry.txt. These checks leave
P1-03 B/P2-02 incomplete. Cold/native/VM/second-model/review-benefit gates also remain;
no independent increment currently has every prerequisite. Next prerequisite: ordinary
permitted acquisition of the isolated MCP SDK or documented embedding model, following
docs/recovery.md and docs/project-memory.md. Do not repeat the closed live trial to
replace its failures or change the default despite its failed quality gate.

## A1b1 actual paired corpus (verified negative adoption decision, 2026-10-26)

The ordinary primary service is available again: local Qwen3.5:9b manifest56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90,
Ollama0.40.7, tool metadata admitted and Studio idle. Application sources match the
closed A1a snapshot. No completed regression was repeated and no application source,
prompt/oracle/default or service setting was changed before starting the live study.

Actual run9b55fdf021e94b37bf7225e6667a3707 completed under supervised session97054,
which returned exit1 and was collected. This is the evaluator's rejected-gate result,
not an infrastructure exception; do not restart it or re-poll its terminal handle.
Parent log: .runtime/p3-02-qualification/live-retry-2ec1e53e378a4d3784429a2aca0150a1.txt.
Individual requests/results/receipts persist under .runtime/probe-qualification/9b55fdf021e94b37bf7225e6667a3707/.
All120 model attempts and16 deterministic safety attempts completed. Both profiles
pass56/60 model tasks (93.3%) and8/8 safety checks with zero observed unauthorized effects.
All source/request/context/native receipts revalidate, and application sources match
the A1a baseline before/after. Exact model/settings identity and original oracles are retained.

Median/p95 full worker latency: fixed2K13.578/17.766s, configured8K7.078/11.750s.
All60 pairs save at least0.2s; median paired gain6.4695s. Median native probe+main loading
falls6.475903s to0.018003s. Native generation rates73.169 versus73.119 token/s are nearly
unchanged; this is loading/worker latency benefit, not faster generation. Maximum sampled
model size_vram is5,862,210,928 bytes in both profiles, not continuous device peak.

The predeclared per-case nonregression gate fails: download passes3/3 baseline versus2/3
candidate, offset in the aggregate by multiple-tabs2/3 versus3/3. Both satisfy the90%
threshold, but equal aggregate totals do not override that separate gate. Do not infer
causation from three repetitions or rerun/relax a failed case to obtain acceptance.
The candidate stays unapplied; controlled cold/runtime adoption remains unaccepted.

Diagnosis: all six recovery-missing-file failures drop only the terminal LF. Published
bytes match the hashed known write request, so no publisher stripping bug is established.
The baseline tabs failure omitted an explicit browser_read; browser_open already returns
page content, which limits that oracle's semantic interpretation. Its version stays fixed.
The candidate download attempt returns a tool error and publishes no file; its exact
error category was not retained, so the lower-level cause is unknown. No policy bypass,
fixture repair or model-output edit was used to change any verdict.

Content-free analysis/diagnosis: .runtime/p3-02-live-20261026/analysis.json and diagnosis.json.
No application/test source changed, so A1a's727-test and wheel gates are reused by exact
source identity; live observations do not turn its62 skipped checks into passes.
Closure evidence/source archive: .runtime/p3-02-live-20261026/validation.json and after.zip.

This service restoration supersedes the primary-unavailable condition below for the
completed run; earlier failed owned-server/model-access diagnostics remain retained.
Residency is ambient, not controlled cold. No shared-model unload or service restart
is authorized by Studio idleness. Read-only process inspection finds the same portable
binary but a different Windows account for the working primary service; that does not
grant this session its native model-store access. A1b1 measurement alone closes.
A1b/overall P3-02 remain unchecked: candidate nonregression failed and cold/runtime
adoption is incomplete. Next independent prerequisite: permitted MCP SDK acquisition;
embedding/second-model, native and VM gates remain separately open.

## A1b owned-model admission retry (blocked before inference, 2026-10-26)

The resumed worktree's Python application sources match the closed A1a manifest, so
completed regressions were not repeated. Primary11434 metadata still fails10061.
A bounded ordinary Python read now succeeds for the existing Qwen manifest: valid JSON,
regular single-link file, no reparse point, and its directory can be enumerated.
This justified one new admission attempt through the existing isolated_server helper.

Owned run b968ad9d97cc414d9e6984f78079bda2 started Ollama0.40.7 on private59323 with
the configured .runtime/models directory, cloud/pruning disabled and no shared-service
control. The API became ready, but tags omitted Qwen and logged manifest Access is
denied; metadata admission raised ValueError. No model generation or comparison ran.
The helper's finally block closed its owned process; cleanup is checked separately.
Raw diagnostic/failure evidence: .runtime/probe-qualification-owned/b968ad9d97cc414d9e6984f78079bda2/;
parent log: .runtime/p3-02-qualification/owned-live-20261026.txt.

Cleanup inspection finds no listener remaining on the owned59323 port. Fresh MCP
dry-runs still fail1 offline and2 online with socket10013; neither installs a dependency.
The current bounded observations and hashes are recorded in
.runtime/roadmap-gates/20261026/gates.json, with separate SDK logs alongside it.

Official Ollama Windows documentation confirms OLLAMA_MODELS controls the store and
ordinary Windows installations do not require elevation. Its published0.40.7 manifest
reader resolves paths, checks metadata and opens the verified manifest; a Python byte
read does not exercise that entire native path. The exact failed OS operation/security
layer is not established. Do not diagnose corruption, change ACLs, copy protected data
around restrictions, re-pull/delete weights or weaken verification from this evidence.

A1b stays unchecked. Next prerequisite: an ordinary-user Ollama service that lists
the configured model, then actual paired quality/safety and separately owned cold checks.
A1a's closed evidence/source archive is preserved. Source-only documentation updates
need no repeat of unchanged runtime tests. Official references:
https://docs.ollama.com/windows and
https://raw.githubusercontent.com/ollama/ollama/v0.40.7/manifest/manifest.go.

## Remaining dependency gate audit after A1a (2026-10-25)

Normal process/file access recovered. Read-only inspection finds no11434 listener and
an API connection refusal10061, so A1b cannot run against an actual model now. MCP is
not installed; isolated offline/online dry-runs fail1/2 with PyPI socket10013. The candidate
embedding cache and NSIS artifact are absent. VM commands are not on PATH and there is
no configured disposable provider/image; this does not prove host virtualization absent.
Restricted-review candidate benefit remains failed; no child is activated. P3-01 has
no demonstrated new input need. No remaining independent increment currently satisfies
all prerequisites, so no unrelated source feature is introduced to replace those gates.

Evidence: .runtime/p3-02-qualification/remaining-gates.json and mcp-*-recheck.txt.
Recovery steps are in ROADMAP.md's current-blockers table. First actionable prerequisite:
start the ordinary user's Ollama through Studio Models and confirm the configured model
is listed; preserve existing security boundaries and service ownership. The completed
A1a validation/source snapshot below remains closed and is not regenerated by this audit.

## P3-02 A1a matched comparison harness (verified protocol scope, 2026-10-25)

The development-only comparator reuses the original evaluation corpus, Agent/Tools,
fixture grants, independent oracles/effects and owned process supervision. Only the
experimental schema-probe context differs. Production Model.admit/defaults stay unchanged.

- [x] Add fixed-profile worker routing and a trusted model-factory seam to evaluation_runner.
- [x] Add probe_qualification:20 model cases/three repetitions and eight safety cases
  per profile, alternating order, bounded workers, immutable requests and private receipts.
- [x] Bind source/model/server/request/initial-prompt/check/metric observations; normalize
  only the exact trusted ephemeral browser origin and preserve all existing permissions.
- [x] Predeclare both original90% quality/safety gates, no per-case quality loss,
  at least80% pairs saving0.2s and at least10% median latency improvement.
- [x] Correct fast-probe timing with perf_counter and a deterministic clock-resolution
  regression; positive-duration validation is preserved.
- [x] Recovered targeted93 tests:90 passed/3 skipped,27.063s. Timing-focused17 pass,7.633s.
- [x] Recovered matrix passes,126.491s:120 simulated-model workflows and16 real safety
  workflows. All60 model cases and8 denials pass per profile. This is protocol evidence.
- [x] Offline wheel/source/import checks and retained protocol-report revalidation pass.
- [x] Full regression727 tests:665 passed/62 skipped,303.792s; Ruff passes.
- [x] Audit requirements, retain failure/evidence/source snapshots and close only A1a.
- [ ] Actual-model paired quality/safety and controlled owned cold comparison (A1b).

Files: local_agent/probe_qualification.py, local_agent/evaluation_runner.py,
local_agent/evaluate_optimizations.py, tests/test_probe_qualification.py and
tests/test_optimization_evaluation.py. The original evaluator worker remains default.
Only fixed_2048/configured select the fixed comparison worker; there is no arbitrary
command/module grant, API endpoint, GUI action, dependency or service-state change.
Receipts in owned state files cannot override independent verifier/effects results.

The initial full matrix failed duration validation after143.741s. Its log remains at
.runtime/p3-02-qualification/protocol-matrix.txt. Recovered logs are alongside it;
all recovered fixtures/observations persist under
.runtime/probe-qualification-protocol/9ed3cac55b5c4c39a74e0b08958ffe31/.
Live attempt9b8dbd74edf54e899389f414b2ae46f8 retained unrun model rows, not a quality score.
Localhost11434 refused connections; a temporary owned Ollama0.40.7 diagnostic listed
no models and logged manifest Access is denied. Only that owned process was closed.

Repeated CreateProcessWithLogonW1909 blocked new checks and progress-document writes.
After the latest user resume, command access recovered; full regression68395 completed
successfully and was collected. Its62 opt-in/environment skips remain unpassed; the
new matrix's separate selected run passed without skips. All Python sources in the
offline wheel match the worktree, the unpacked wheel imports independently and its
comparison code revalidates all retained protocol observations. Wheel SHA:
9b34b57039543a338092d31c163f01d6b552dee630fc63b1e99d603dc8d9c60f.
No Studio/runtime import path depends on these development evaluator modules, so no
frontend, native executable or installer was rebuilt for this source-only increment.

Current metadata retry still fails with URLError; it establishes no model availability
or inference result. MCP remains absent; fresh dry-runs exit1 offline and2 online, with
PyPI socket10013. No environment dependency is installed and no alternate transport or
permission workaround is used. Existing embedding/native/VM/routing gates remain open.

A1a closes; A1b/overall P3-02 remain incomplete. The next increment is actual-model
paired quality/safety and controlled owned model-unloaded qualification, then runtime
adoption only if its original gates pass. Shared-service model unloading is not justified
by Studio idleness alone: an isolated owned server with ordinary model-store access is
the preferred cold boundary. Current access prevents that validation; do not restart or
unload an unrelated service. Earlier A0 evidence/writers remain closed. Guide:
docs/probe-qualification.md; closure: .runtime/p3-02-qualification/validation.json.

## P3-02 A0 schema-probe context feasibility (verified warm-only, 2026-10-25)

The review trial observed2.832s compatibility preparation then3.553s first-role model
load, versus2.7–3.4ms later loads. Current Model.admit hardcodes probe num_ctx2048 before
normal8192-context requests. Official Ollama documents num_ctx as the runtime context
and load_duration as native loading time. This supports investigating a context-switch
hypothesis, not applying a default or claiming causation yet.

- [x] Inspect current Model.admit, inference tests, native observations and existing optimization/benchmark/evaluation helpers; review official API parameter/timing docs.
- [x] Extend the existing optimization evaluator with a development-only warm-probe comparison using fresh owned workers and only a request-local probe-context override.
- [x] Preserve original runtime defaults, prompt/output/thinking/approval guards and service ownership; no unload/restart/download or alternate-network path.
- [x] Run six alternating profile pairs, verify observed contexts/VRAM, invariant payload hashes, exact counter microtask and bounded native/process timings.
- [x] Add positive/negative protocol/control/provenance tests and run relevant regression/lint/package checks.
- [x] Record warm-only feasibility and limitations. Keep full P3-02/adoption open pending cold/quality qualification.

Files: local_agent/evaluate_optimizations.py, tests/test_optimization_evaluation.py and
experiment documentation. Reuse existing Ollama, InferenceOptions, PROBE_SCHEMA,
run_process, Policy, benchmark case/idle/GPU helpers and strict evaluation utilities.
New CLI branch must return before the old isolated-server/unload path. Main application
Model remains unchanged during feasibility. Existing P2-04/P1-06 evidence is closed.

Added --probe-context and an early-return hidden owned-worker path to the existing
optimization evaluator; the original isolated-server/residency path is unchanged.
ProbeContextModel modifies only the experimental probe's num_ctx and verifies the
unchanged64-token/temp0/no-tool/no-truncation/no-shift contract. The parent metadata
preflight uses the existing owned model probe; warm-up and all measured requests are
inside supervised workers. No global capability cache mutation or user-service stop.
Six new/previous optimization tests verify protected fields, copied caller data,
actual receipt handling, bad metrics/order/payloads, fixture provenance and CLI routing.

Actual run5593113dc9964b1aaf55dd6107a3c9f0 completed all12 samples/six alternating
pairs, all exact counter values correct. Normalized probe/main payload hashes match;
Ollama reports probe contexts2048 versus8192 and main contexts8192 throughout. Warm
setup is measured separately inside each worker and subtracted from total process
wall time; the unadjusted process and request times remain available.

Fresh-worker-without-warm-setup p50/p95: fixed2K8.218/8.282s, matched8K1.047/1.079s.
Paired savings6.547–7.219s across all six pairs. Median native probe+main loading:
7.091163s versus0.007032s. Maximum sampled model size_vram is5,862,210,928 bytes in
both profiles, not an independent continuous device peak. These observations support
warm context reconfiguration/loading cost, not higher generation throughput. First
setup started with no resident model, but it is not a matched cold comparison.

Default regression715 tests:654 passed/61 skipped,297.075s. Targeted50:49 passed/one
existing actual-model opt-in skipped,15.573s. All6 optimization tests and Ruff pass.
Offline wheel contains byte-matching source and imports independently (SHAd50911b020364e98e2e5d6f5a9d05b45f4221fab1a78a844fda80823a27719bd).
No production Model/GUI/config/default/installer change. Raw native receipts and sources:
.runtime/probe-context-trials/5593113dc9964b1aaf55dd6107a3c9f0/; closure evidence:
.runtime/p3-02-probe-context/validation.json. Guide: docs/probe-context-trial.md.

A0 warm feasibility closes with positive evidence. P3-02/adoption remain incomplete:
broader matched agent-quality/safety, controlled model-unloaded conditions and final
runtime regression/packaging must pass before changing a default. Next: qualify this
one request-local setting with the existing evaluation runner/oracles; preserve every
failure and confirm ownership before any cold-model control. No service restart/unload
was performed by A0, and no old evidence writer was rerun.

## P2-04 A0 restricted-review evaluation prerequisite (verified, 2026-10-25)

P1-06 B has closed. Fresh dependency check still lists only qwen3.5:9b, no candidate
embedding cache and no installed/isolated MCP SDK. Prior separate-cache registry10013
restriction remains; the existing user's service is not used as a download proxy.
Those gates remain open. The restored chat model makes P2-04 evaluation actionable.

- [x] Read F09/roadmap and inspect existing Agent, inspection, policy, model, native metrics, process supervisor and evaluation code.
- [x] Add a fixed bounded source-anchored report schema and immutable trusted review fixtures/oracles.
- [x] Add an optional development-only paired trial using existing local-model/policy/process helpers; no Studio tool/endpoint/default delegation.
- [x] Compare one pass, same-agent self-review and independent specialist review on identical seeded inputs. Equal two-pass budgets prevent attributing extra effort to specialization.
- [x] Add positive/negative/injection/scope/malformed/changed-input and incomplete/fixture-provenance tests; verify trusted fixture defects independently.
- [x] Run all eight cases three times with actual model/native observations and record failures/identity/latency; report measured benefit or its absence without changing the oracle.
- [x] Run relevant regression/lint/package-content checks and close only this evaluation prerequisite if satisfied.

Planned files: local_agent/review_trial.py (fixed development contract/fixtures/runner),
tests/test_review_trial.py, docs/specialist-review-trial.md and project progress documents.
Use existing Ollama structured output, Coding/Policy reads, resource fingerprints,
owned run_process supervision and evaluation metadata helpers. No new dependency or
framework. Full P2-04 still requires integrated parent/child task records, inherited
permissions/budgets, stop propagation and verified review behavior before activation;
this prerequisite does not redefine or satisfy that entire feature.

Implemented local_agent/review_trial.py and11 focused tests. The private fixed report
rejects unknown/duplicate fields, foreign anchors, invalid status, credentials, missing/
nonfinite native observations, widened grants, mixed model/protocol identities and stale
source versions. Trials use one model-readable subject.py, no tool dispatch or recursive
delegation, three ordinary model calls plus at most one bounded schema probe per worker.
One pass is shared with equal-budget self-review and fresh specialist alternatives;
their order is counterbalanced12/12. Global elapsed limit600s and owned-worker limit100s
include existing supervisor cleanup behavior, with startup/cleanup overhead documented.
These are development role records/budgets, not integrated Studio child task authority.

Actual protocol1 completed24 inputs/72 ordinary model calls: exact-location counts6/24
first pass,9/24 self-review,6/24 specialist; zero wins and three regressions. Most defective
cases returned no_findings. The schema was not in the prompt and source was an escaped
string; official Ollama guidance recommends grounding schema text. This complete negative
run/source/wheel remains in v1-evidence.json and v1-source.zip, rather than being replaced.

Protocol2 adds generic schema-in-prompt grounding and numbered source lines. The eight
fixtures, tests and exact-location oracle are unchanged (corpus6164737577ee2183accf837d1c62ec5913ccc29e068812345bd128757fbe82a6).
Actual24 inputs/72 calls completed: first pass18/24, self-review21/24, specialist19/24;
zero specialist wins over self-review and two regressions. Benefit gate is false.
Both protocols used existing local qwen3.5:9b/Ollama0.40.7 with per-case before/after
manifest/settings checks. All ordinary responses finished stop with bounded native
counters. No service restart/unload, model download, cloud call or security change.

Protocol2 observed workflow p50/p95 seconds:8.231/9.377 first pass,9.260/10.664 self-review,
9.352/11.259 specialist. Mean specialist-minus-self second-pass cost+0.090s. Native4391
generated tokens/64.723277s generation is67.843 token/s, not end-to-end throughput or a
controlled GPU benchmark. Workflow timing includes shared preparation plus role calls,
excluding worker start/final identity/cleanup; process.json retains broader process cost.
These are exploratory revisions on the same fixtures, not held-out prompt-quality proof.

Validation: protocol2 full default709/648 passed/61 skipped,301.316s before the final
defensive first-source guard. Final targeted70/69 passed/one existing live opt-in skipped,
19.807s, include all11 new contract cases. That opt-in native output-limit/timing case
was then explicitly enabled and passed separately; the combined-run skip remains recorded.
Ruff passes. The final guard binds the created
source across schema-probe time; a real-file replacement test proves it never reaches
source-bearing inference. AST comparison proves prompts/schema/options/corpus/aggregator
unchanged; all24 retained source snapshots match current guard predicates and independently
reproduce the same summary. No new full710-test claim or model rerun is implied.

Offline actual-trial wheel source/import is verified. Guarded final wheel source matches
current module (SHA0137fb22de49796c6d49aa7bd64e0f0e559dc54bba9f98e8ba1ac3426ba573bf);
the actual protocol2 source wheel is retained separately (d6ba7140771cb9b738b3d849a41a9105abbeda5c68b30c22c8c9a6edcc40e6a2).
No activated backend/frontend/config/dependency changes. Existing P1-06/B1 evidence
writers were not rerun. Current raw runs are106d06fdea764917acf27263d3658269 and
d805628ae96c4dc3ab6dd4cd4f62851a under .runtime/review-trials/; closure evidence is
.runtime/p2-04-review-trial/validation.json. Guide: docs/specialist-review-trial.md.

Decision: A0 evaluator closes; full P2-04 child feature stays incomplete and inactive
because the candidate failed its predeclared benefit gate. No inference-quality failure
was relabelled passed, removed or rerun to replace a bad repetition. Next safe independent
candidate: P3-02 controlled investigation of the observed load overhead. One observed
first-role native load was3.553s versus2.7–3.4ms on later roles, after a2.832s compatibility
preparation. Probe context2048 versus requested8192 may reconfigure the runner; this is
a hypothesis requiring matched actual trials and quality gates before any default changes.

## P1-06 B2b remaining actual-model message/export acceptance (verified, 2026-10-25)

- [x] Review current source/tests and every still-open B2b/B2/B requirement; distinguish implemented paging/export from missing validation.
- [x] Recheck real-model readiness and shared-resource idleness before model work; preserve the source/document boundary and existing screenshots.
- [x] Run both actual-model chat/slash UI scenarios with isolated backend/data and the existing frontend; no unrelated service termination.
- [x] Confirm current message/export/approval/reconnect regression evidence still matches application source; fix any reproduced failure and verify affected behavior.
- [x] Record actual verdicts/limitations and close only satisfied B2b/B2/B checkboxes.

The previous turn restored configured model access. Message paging/export is already
implemented; no application changes are planned absent a reproduced failure. The real
UI harness supports reusing the user's frontend while its native connection bridge
targets disposable backend/database instances. The existing Ollama service is reused,
not started/stopped. New logs/snapshots: .runtime/p1-06-messages-recovered/. Historical
failed UI and owned-service attempts remain unchanged in .runtime/p1-06-messages/.

Both actual-model scenarios passed/zero skipped in62.526s, reusing existing qwen3.5:9b
on Ollama0.40.7 (manifest56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90).
Chat attachment response, previews/removal/drop, export/delete and slash/goal/model/
planning/regeneration, actual tool work, denied/approved tests and cancellation pass.
Native connection IPC is bridged; backend, storage, sockets, workers and inference are real.
No unrelated service was started/stopped. Before retry,180 application/test files matched
the closed B1 boundary exactly; the private before snapshot preserves old screenshots.

Fresh affected UI3 initially had2 passes/1 failure (47.566s): the browser preview was
still in browser_open when its unchanged30s assertion expired. Read-only GET proved
the shared Vite /scoped-preview URL returned Local Agent Studio HTML and lacked the
fixture marker. This is a definite isolation gap, not proof that all startup latency
is explained. The scoped test now reuses FixtureSite on its own ephemeral approved
origin and asserts actual tool-result URL/title/text before checking screenshot/scoping/
approval behavior. The obsolete shared route was removed. No timeout, oracle, policy or
production browser code was weakened. Retained failed log: affected-ui.txt.

After the fixture change, all3 affected source UI checks pass/zero skipped in22.236s;
all3 checks against the existing final packaged backend pass/zero skipped in26.756s.
All20 history tests pass/zero skipped in8.487s; all3 discovery checks pass/zero skipped
in0.189s; Ruff passes. The prior699-test product regression (638 passed/61 skipped),
56 packaged gates, TS/Vite/23 Node and33 archived source matches are reused because all
production source/assets/executable are unchanged. The one changed test fixture is
covered by fresh source/packaged checks. No new full-regression or native-install result
is claimed; skipped checks remain unverified. New closure evidence and hashes:
.runtime/p1-06-messages-recovered/validation.json and after.zip.

P1-06 message/export, B2b/B2 and parentB now close at source/browser UI scope, alongside
their previously verified conversation/task/dialog/backup/restore/retention components.
Installed native-product acceptance remains P0-05. Next: reassess P1-03 B embedding-model
acquisition and remaining dependency/native gates before P2-04 specialist implementation.

## Model connection restored on user-requested retry (2026-10-25)

The existing configured service at127.0.0.1:11434 is now reachable from the managed
session, lists qwen3.5:9b and passes the production tools-metadata admission check
(Ollama0.40.7). One actual text request completed with response OK, finish_reason stop,
two generated tokens. No service was started or stopped and no application configuration
changed. This clears the current connection/model-visibility blocker for P2-04; historical
failed checks below remain intact. It does not prove the portable owned-server permission
issue was repaired, actual tool execution, GPU acceleration or review benefit. No new
performance claim follows from a two-token smoke check. SDK/native/VM and other gates
remain separate. Evidence: .runtime/p2-04-review/model-restored-20261025.json.

## Next-increment dependency review: P2-04 remains blocked (2026-10-25)

Continuation audit3 (23:03 UTC): same external prerequisites for the third consecutive
goal turn. Fresh configured-service metadata still fails with URLError; MCP remains
uninstalled and neither the isolated SDK probe nor workspace cache has been prepared.
The previous turn was no progress, not a verified wait; no live handle is being awaited.
No safe independent increment has acquired its required model/SDK/native/VM/input
prerequisites. Goal execution is blocked pending restored access, not complete. No
application changes, service restart, inference, download, permission changes or new
test-pass claims. Evidence: .runtime/p2-04-review/blocked-audit-3.json. Resume after
following the current model/SDK steps in docs/recovery.md; recheck prerequisites then.

Continuation audit2 (23:02 UTC): the prior turn made progress by closing B1. Fresh
read-only metadata again fails with URLError and finds no loopback model listener;
the MCP SDK, isolated probe environment and workspace SDK cache are still absent.
No model service was restarted, no inference/download attempted and no application
code or completed evidence snapshot changed. Reconsidered independent review work:
the remaining acceptance requires a demonstrated benefit/verified review and latency;
an unvalidated specialist implementation would not satisfy that gate. Native/VM and
optional input/model trials retain their documented external prerequisites. Current
evidence: .runtime/p2-04-review/blocked-audit-2.json. No new tests were run or claimed.

After closing P2-03 B1, inspected the actual inspection coordinator/worker, manager,
registry, observability and F09 contract. Existing selected-file read-only execution is
reusable; specialist parent/child records, inherited budgets and verified review contracts
are missing functionality, not merely untested. Acceptance also requires a paired actual
model comparison showing benefit or clearer verified review with measured latency. No
specialist application feature was added or activated without that evidence.

Fresh configured-model metadata check timed out. Read-only listener inspection found no
listener on the configured loopback port11434. The existing ProcessOutput ownership path
then started the portable Ollama service with its configured project model store: the
API became reachable but listed zero models and the bounded owned log contained Access
is denied. No download or inference occurred. Its owned process was closed; no unrelated
Python/Ollama process, account, ACL or security configuration was changed. This does not
mean the user's normal-session model is absent or that historical successful live tests
are invalid. It blocks this session's paired review/model/UI/embedding/routing gates.

P2-02 SDK gate was independently rechecked: mcp is not installed; no SDK files found in
workspace/default uv cache. Isolated dry-run exit1 offline (candidate unavailable), exit2
online (PyPI socket10013). No dependency or application environment was modified. No
configured VM provider/image exists; Get-VM/VBoxManage/vmrun remain unavailable on PATH
(not proof the OS cannot virtualize). Native installed-product and interactive desktop
gates remain separate. Optional P3 ingestion still has no selected demonstrated input
need; optimization/routing trials require real models. No independent remaining feature
was activated to replace missing external prerequisites.

Evidence: .runtime/p2-04-review/preflight.json, listener.json, owned-model.json and the
two SDK dry-run logs. Instructions in docs/recovery.md cover normal-session model access
and an isolated SDK candidate environment. Next actionable implementation: real pinned
MCP handshake when SDK access is restored, or P2-04 paired review after model access is
restored. No checkbox for these blocked increments was marked complete. The B1 evidence
writer/snapshot is closed and was not rerun after this later documentation review.

## P2-03 B1 durable directory-triggered inspections (verified, 2026-10-25)

- [x] Inspect the existing snapshot/queue/scheduler/coordinator/lifecycle/API/UI and migration fixtures; preserve the pre-change boundary.
- [x] Own and bound fixed-protocol directory/model children without widening execution authority.
- [x] Persist scope-bound baseline/candidate/debounce/generation state and exact trigger/source binding; atomically coalesce and queue accepted changes.
- [x] Integrate serial observation/admission with shared pause, disable, shutdown, restore drain and fresh selected-file/model checks.
- [x] Add authenticated project-scoped watch controls and DirectoryWatchPanel with status/latest task; retain interval controls.
- [x] Verify actual changes, internal-state/generated-output exclusions, incomplete scans, restart/crash/deduplication/conflicts and stale/foreign inputs.
- [x] Diagnose the full-regression namespace counterexample, reopen B0 and verify bounded filename revalidation, entry budgets and STOP.
- [x] Pass final source/API/rendered/frozen/regression/lint/build gates, compare archived code and document limits.

Schema8 adds directory_watches/directory_runs. Watches use the existing Scheduler,
WorkQueue and read-only inspection worker. Initial complete observations establish a
baseline only; matching changed observations separated by debounce may enqueue one
inspection. Incomplete observations clear candidates and never authorize work. Baseline,
generation and unique trigger receipt commit together; one pending run coalesces changes.
Exact request/conversation/source binding prevents foreign or ambiguous queue admission.

The private probe protocol permits only fixed model/directory observation kinds. Owned
children are released after Job ownership; replies are bounded to64 KiB and reject
malformed/duplicate/nonfinite values. A separate bounded reader prevents a partial frame
from blocking the parent's deadline or cancellation. Directory parent deadline is4s,
model metadata8s; startup/cleanup add overhead. Constructor/Job/reader faults clean up
owned resources and preserve unrelated processes. No OS isolation claim follows.

Authenticated watch routes and Workspace controls support enable/disable, shared durable
automatic-work pause, status and existing-task navigation. Disable cancels pending work
and invalidates in-flight admission; an admitted task has separate Cancel. Re-enable
starts a fresh baseline. Emergency stop persists pause; resume is explicit. Restore
changes database identity rather than silently granting old authority. Backup/retention
cover watch/run rows and reject cross-conversation links. Invalid stored identifiers
are not echoed into responses. No dependency or existing configuration was replaced.

**Failure diagnosed:** the first full698-test run failed one namespace-change assertion
(61 skipped,305.238s). A late addition can leave directory stat signatures unchanged.
Restoring the timestamp after creating late.py reproduces the production gap reliably
(1 failure,0.008s). B0 was reopened. The observer now enumerates names again, sharing
entry/time/STOP budgets and never opening late arrivals; a changed set is incomplete.
The original failure and deterministic reproduction remain in regression.txt and
namespace-reproduced.txt. Neither assertion nor acceptance criteria were weakened.
Windows1909 temporarily prevented commands/writes; access recovered without account,
ACL or security changes. Existing process handles were collected before new runs.

**Final evidence** (.runtime/p2-03-directory-workflow/validation.json):

- Full regression:699 tests,638 passed/61 skipped,301.966s. Skips remain unverified.
- Expanded targeted:172 passed/zero skipped,88.793s; namespace fix focused61 passed/zero skipped,31.302s.
- Rebuilt packaged UI/HTTP/runtime/socket/loop:56 passed/zero skipped,288.571s.
- Source900px directory and interval UI:2 passed/zero skipped,17.712s. Final packaged gate repeats both workflows.
- TypeScript/Vite,23 Node tests and Ruff pass. No frontend change followed the recorded build.
- All33 reviewed archived runtime entries equal source; final executable SHA256 f638e524dad4b38e6cf4f1104fe61bcad6acb068928532a469fc531b9b02c7de.
- Assets index-Pe-_u9We.css/index-D6X70P6d.js;900px screenshot inspected. Source hashes, immutable before/after snapshots and retained failed runs are recorded.

B0/B1/B close for Studio-only selected-file read-only inspections. Scans are serial with
at least5s rescan delay and defer to active work. Matching polls are not proof of continuous
stability; UTC downtime counts toward debounce and between-poll changes can be missed.
The two scans share a2,000-entry cap; other observer budgets remain explicit. No automatic
edits/commands/browser/desktop authority, always-on service, webhook, atomic filesystem
snapshot or crashed-task replay is introduced. Private backup data is unencrypted.
Inference/native IPC in these integration tests are explicit fixtures; actual-model
quality, installed native-product acceptance and OS isolation remain separate gates.
Guide: docs/directory-inspections.md. Next: assess P2-04's restricted review/evaluation
prerequisites and recheck external dependency/model gates before activating more work.

## P2-03 B0 bounded directory observations (verified; namespace fix reverified in B1)

- [x] Close A/A1 with final logs, document updates and immutable evidence snapshot.
- [x] Inspect actual policy/link checks, repository-search exclusions, fingerprint helpers and F08/B contracts.
- [x] Snapshot the boundary and review official Python scandir/stat behavior.
- [x] Add private bounded recursive directory snapshots with identity/content fingerprints and explicit incompleteness.
- [x] Verify ordinary changes, unchanged inputs, links, concurrent mutation, credentials/state/output exclusions and resource limits.
- [x] Run relevant regression/lint checks and record verified B0 scope and remaining B1 work.

B0 does not register a tool, API, timer or automatic work. B1 must add durable baseline,
debounce and trigger association through the existing scheduler/coordinator. No new
dependency is required. Snapshot contents are private path/hash metadata, never file
contents, model instructions or execution authority. Incomplete observations cannot
establish an unchanged directory or generate a valid fingerprint.

First component/search run:29 tests passed/zero skipped in2.009s. Expanded boundary
checks found a fixture issue: Windows prevents renaming a parent while its file handle
is open. The actual replacement now happens after file/scandir closure and before final
revalidation, preserving the identity-conflict assertion. The retained targeted.txt
records54 tests/one fixture error/one legacy skip. Corrected targeted-final.txt passes
53/54 with one legacy Windows symlink-creation skip in6.226s; all14 snapshot cases pass,
including actual junction/hardlink and late hardlink detection before any content read.
Ruff passes. Final default671 tests ran in270.338s:611 passed,60 skipped. All14 snapshot
cases pass without skips; the targeted skip is the existing unavailable Windows symlink
creation case. Real junction/hardlink and late-link-before-read checks pass. The first
full run retains the same fixture error (671 tests/one error/60 skips,270.430s); the
corrected full run above passes. No failed or skipped observation is promoted to success.

The helper reuses Policy, resource signatures and repository-search exclusions without
modifying those working components. It hashes approved regular-file bytes, returns only
private relative paths/version/content hashes, and rechecks file/directory identity.
Same-size/same-timestamp edits still change content fingerprints. Count/byte/depth/time/
manifest budgets and unreadable/concurrent inputs produce no valid fingerprint. Limits
are cooperative between OS calls, not a hard blocked-IO deadline or an atomic snapshot.

All59 reviewed existing runtime/frontend files, assets and packaged executable equal
the A1 boundary, so its TS/Vite/23 Node/52 packaged checks are reused, not rerun or
relabelled as new B0 tests. The source-only helper is not yet imported by the activated
runtime or bundled; B1 must own observation execution and add durable debounce/trigger
association, permission/lifecycle checks and actual API/UI acceptance. No new dependency,
model tool, endpoint, timer, persistence or automatic work is added by B0.
Guide: docs/directory-observations.md. Evidence: .runtime/p2-03-directory-snapshot/
validation.json and after.zip. B0 closes; B/B1 stay open and are next.

## P2-03 A1 interval inspection workflow (verified 2026-10-25)

- [x] Inspect A0, actual inspection admission, FastAPI lifespan, restore drain, UI and regression fixtures.
- [x] Snapshot A0 and review official SQLite/FastAPI/Intl documentation.
- [x] Persist bounded read-only intervals, UTC next-run/skip-or-coalesce policy and explicit display timezone.
- [x] Dispatch through owned bounded model preflight and existing queue/inspection coordinator, preserving scope/stop/resource/restore guards.
- [x] Add authenticated enable/disable/pause controls and rendered Studio UI with latest task and explicit scheduler resume.
- [x] Verify restart/dedup/expiry/conflicts/disabled/DST/stop/shutdown/restore and actual HTTP/UI paths.
- [x] Run final regression/lint/frontend/package checks, compare archived source and retain evidence.

Schema7 adds interval_schedules/schedule_runs; Scheduler reuses WorkQueue, Manager and
the existing inspection worker. Slots advance and enqueue atomically, with stable trigger
keys and exact queued payload/conversation/schedule/due-slot binding. One pending item
per schedule coalesces busy slots. Intervals are elapsed UTC (1 minute–30 days); saved
IANA zones affect display only. Skip and latest-slot coalescing are explicit and tested
through both Toronto DST transitions. Limits:50 schedules and existing queue byte/count
caps; malformed records never become public status or automatic authority.

The timer lives only inside FastAPI lifespan, participates in the restore request drain
and stops with its owned runtime. Metadata preflight has an eight-second parent deadline
in an owned process; pipes/process/Job cleanup is registered even for constructor or
ownership failures. Normal supervision rechecks model/file identities before tools.
Disable cancels pending/in-flight admission, leaving admitted tasks with separate Cancel.
Emergency stop remains available while connected and persists an automatic-work pause;
explicit confirmed resume is required. No background Windows service, webhook, directory
trigger or unattended mutation is added. Selected-file reads receive no prior chat,
memory, image or non-read tools. Current file contents are inspected on each run.

Backup/restore fixtures contain schedule/run rows, schema6-to7 rollback preserves data,
enabled schedules protect bulk retention and cross-chat run relationships block deletion.
Restored store identity invalidates old automatic authority. Saved records are private,
unencrypted backup content. Committed trigger admission never automatically replays a
crashed task; this is not exactly-once execution or OS isolation.

Final verification:657 default tests,597 passed/60 skipped,285.348s;131 targeted tests,
zero skipped,56.798s; source schedule UI1/zero skipped,7.372s. All52 final packaged
UI/HTTP/runtime/socket/loop tests pass/zero skipped in244.856s. The focused packaged
history regression passes1/zero skipped in14.619s. Strict TS/Vite,23 Node tests and
Ruff pass. All30 reviewed archived runtime code entries equal source. Backend SHA256:
4b1919a3e6b3ce8932f99d9e0602301a39de9628a09f97342d56b95d5cd21067.
The full Python baseline precedes the final frontend-only history fix; the complete
packaged regression and final frontend build verify that fix. Skips are not passes.

Retained failures: foundation-first.txt records outdated schema/fixture assumptions;
source-ui-first.txt records a Playwright cleanup-order fixture error. Saved-record and
date negatives reproduced missing exact binding/status guards and invalid-date rendering;
new regressions now pass. The first packaged failure used disabled idle Emergency stop
as a completion signal; it now polls actual terminal status. The next exposed a real
history pagination race: stale rows stayed clickable while an older page loaded. A held
real HTTP response reproduces the bug; TaskHistory now disables those rows. A follow-up
ambiguous heading locator was corrected to level2. All failures remain under
.runtime/p2-03-interval, alongside final passing logs.

Windows1909 intermittently blocked commands and progress writes. Existing test handles
were collected without restarting completed work; recovery changed no account/ACL/security
settings. Rendered inference/native IPC are explicit protocol fixtures; actual-model
quality, native installed-product and other roadmap gates remain separate.
Guide: docs/interval-inspections.md. Evidence: .runtime/p2-03-interval/validation.json,
frozen-identity.json and after.zip. A/A1 close; next independent increment is P2-03 B,
debounced approved-directory observations with durable identity and self-output exclusion.

## P2-02 MCP dependency gate (blocked 2026-10-25)

- [x] Audit current immutable ToolSpec/profiles, journal effect classification and missing MCP integration.
- [x] Review official SDK/PyPI documentation and installed Python/dependencies; no SDK is installed.
- [x] Test ordinary offline and online dry-run dependency resolution without changing the application environment.
- [ ] Acquire a compatible pinned SDK and verify actual stdio handshake/list/call before implementing or enabling an adapter.

Candidate mcp2.3.0 is the official stable2026-10-02 release and declares Python>=3.10;
this checkout uses Python3.12. That establishes only Python-level eligibility, not verified
transitive/API/runtime compatibility. Main-branch docs differ from the pinned release;
use the acquired version's actual APIs. Current FastAPI0.159.1/Starlette1.9.0/httpx0.28.1/
AnyIO4.15.1/Pydantic2.14.1/Uvicorn0.54.0 must remain working.

uv0.12.18 offline dry-run finds no cached mcp2.3.0 (exit1). The normal online PyPI dry-run
fails immediately with socket10013 (exit2;5s timeout,zero retries). This is package access
blocked by socket permissions, not evidence that DNS or MCP protocol compatibility failed.
No package was installed, no dependency/lockfile or application functionality changed,
and no network/account/ACL setting was modified. No mock provider was added or acceptance
claimed. Evidence: .runtime/p2-02-mcp/acquisition.json and both resolver logs.

Recovery: make the official pinned SDK/dependencies available through ordinary package
access or a reviewed workspace cache, resolve against existing pinned app versions in an
isolated trial environment, then run real handshake/list/call/cancel/scope/schema tests.
Do not weaken TLS/network controls or replace a working environment merely to resolve it.
P2-02 remains open. Next independent work is P2-03 A's durable queue-lease prerequisite.

## P2-03 A0 durable queue admission leases (verified 2026-10-25)

- [x] Inspect current task admission, checkpoint single-consumer transactions, state ownership and F08/P2-03 contracts.
- [x] Snapshot before changes and review SQLite transaction/atomic-commit documentation.
- [x] Add schema6 bounded private queue, stable trigger deduplication and expiring owned claims.
- [x] Bind one fresh read-only task atomically to a current claim; reject stale/forged/changed/cancelled claims.
- [x] Verify concurrent claims/admission, crash before/after commit, stop/conflicts and no replay of admitted work.
- [x] Verify migration/backup/restore/retention integration and source/default/frozen regression gates.
- [x] Implement independently testable durable trigger IDs/leases and atomic association with task admission; never requeue an admitted task after crash.
- [ ] Integrate one read-only interval workflow through the existing coordinator, with disable, explicit timezone/misfire behavior and persisted next run.
- [ ] Verify duplicate/restart/lease-expiry races, resource conflicts, stop/shutdown, DST/display, disabled work and real API/runtime/UI paths.

Scheduling/automatic dispatch is not implemented yet. A0 adds private queue primitives and
optional atomic inspection admission; it does not expose a new model tool or start timers.
Existing state-root and screenshot leases remain separate ownership controls. No new
dependency is required. UTC elapsed intervals can avoid ambiguous/repeated local
wall-clock slots; timezone display must remain explicit and tested through DST. tzdata is
not installed, so avoid assuming Python ZoneInfo has an IANA database on this Windows host.
Keep the complete P2-03 A acceptance gate open until the interval workflow and controls
are integrated; a lease-only prerequisite cannot complete scheduling.

Implemented work_queue.py and schema6 using existing SQLite transactions, not a new job
framework. Exact retained trigger/payload/conversation deduplication survives restart.
Claims store token hashes only; current owner, nonce and expiry must match. Task admission,
initial checkpoint and queue consumption commit together. Admitted items never requeue,
including lost acknowledgement and missing task history. This is at-most-one retained
admission, not exactly-one execution. Real process crashes before/after the commit and
concurrent claim/admission tests verify the distinction. Files/model are checked afresh
at admission; file contents are not pinned by enqueue. Leases use UTC wall-clock expiry.

Store/Manager/inspection accept a private optional claim; ordinary modes cannot consume
one. No claim nonce is sent to a worker, model, event or public summary. Existing scope,
stop, ownership, busy and shutdown guards are preserved. Pending work protects bulk
retention; exact previews include queue rows and cross-chat queue/task links are rejected.
Nonempty queue rows participate in existing backup/restore fixtures and migration5-to6
rollback preserves checkpoint/history data. Queue storage has explicit count/byte/scan caps.

Verification:97 targeted tests passed/zero skipped in36.410s;633 default tests ran in
252.510s:574 passed,59 skipped. All48 final packaged UI/HTTP/runtime/socket/loop regression
checks passed/zero skipped in236.934s. Ruff passes. Frontend code/assets are unchanged
and hash-equal to the verified P2-01 TS/Vite/19 Node boundary; no UI build was repeated.
All27 reviewed archived code entries match current source. Backend SHA256:
f5953861a052495a2a1f3744c32de4b3e31228c507cd5da14d96933344ef137e.
The first queue run retained one fixture error (test deletion omitted an events FK);
the fixture was corrected without weakening constraints. Lint-only test/import mistakes
were fixed before the final runs. Source worker/model protocol fixtures do not establish
actual-model quality; packaged checks do not establish a scheduling UI that does not exist.

Managed Windows1909 interrupted final documentation/comparison after the tests finished.
Access recovered without account/ACL/security changes; no completed test was restarted.
Evidence: .runtime/p2-03-queue/validation.json, frozen-identity.json and after.zip.
Guide: docs/workflow-queue.md. A0 closes; A/A1 stay open. Next: persisted interval workflow
with disable/misfire/timezone, bounded coordinator admission and stop/restore lifecycle.

## P2-01 bounded read-only inspection checkpoint (verified 2026-10-25)

- [x] Audit F06/P2-01, actual Agent/worker/supervisor/journal/schema and desktop integration.
- [x] Review official SQLite transaction and Ollama tool-message documentation; snapshot before edits.
- [x] Add versioned bounded checkpoint storage and exact selected-file preconditions with migration/cascade tests.
- [x] Integrate real agent continuation, durable completed-step acknowledgement, deferred pause and linked explicit resume.
- [x] Restrict this mode to selected UTF-8 file reads; recheck current scopes, model/config/version and reject changed inputs or stale approvals.
- [x] Add authenticated API and desktop controls; other modes remain non-resumable.
- [x] Verify worker/backend restart/crash boundaries, denial/stop/cancel races and positive/negative/regression behavior.
- [x] Run relevant source/default/frozen/rendered/build/lint checks and record evidence before closing P2-01.

The supported workflow is model-driven inspection of1–8 explicitly selected UTF-8 project
files, up to64KB each. It receives no old conversation, memories or attachments and has
only the read_file tool. Existing agent modes keep their current behavior. Checkpoints
contain a bounded validated transcript of completed read-only decisions, never process,
browser or desktop handles. Resume creates a linked task with the original model/options,
remaining step budget and unchanged project/file preconditions. A pause request becomes
paused only after a durable completed-step acknowledgement and owned-worker cleanup.
The supported subset passes real worker/runtime restart and policy acceptance using
explicit inference/native-IPC fixtures. Actual-model quality and native installed-product
acceptance remain separate; this does not enable pause/resume for ordinary agent tasks.

Schema5 adds bounded version1 JSON checkpoints linked to tasks. The fixed trusted prompt,
completed read call/results, file hashes/resource versions and remaining step budget are
validated before storage and restored use. The parent requires matching completed journal
operations before committing/acknowledging a boundary. Resume atomically consumes one
source checkpoint and creates a linked task; old results/journals remain intact. No
pickle, approval body, hidden reasoning, process handle or external-effect replay exists.

Selected files must remain UTF-8, single-link, inside the approved project and outside
private app state. Current project identity, file identities/bytes, model digest/Ollama
version, execution limit, prompt/tool-schema version, memory-forget epoch and store ID
must still match. Restore into a new store requires a fresh inspection. The model cannot
complete a report without observed reads of every selected file. Cancel closes the
continuation; emergency stop during metadata admission invalidates a late worker start.
Checkpoints are at most1MiB; at most3 linked attempts retain the original step limit.
Per-task supervision deadlines apply separately to attempts; no total elapsed-time promise.

Final default620 tests /561 passed /59 skipped in248.331s. All130 targeted checks passed
before the late image-ordering fix (54.004s); all32 affected image/agent/continuation checks
passed afterward (14.107s), including the new regression. Final source HTTP restart/crash
passed2/2 in6.807s. Source rendered inspection passed1/1 in7.873s; all48 final packaged
UI/HTTP/runtime/socket/loop checks passed without skips in236.974s. Strict TS/Vite,19 Node
checks and Ruff pass. All26 inspected archived code entries match current source.
Sidecar SHA256:ad5ecbc1595035466e6d8792d58aa1ddeecb990220dd55f6b1a7da90fc021278.

Coverage includes before/after checkpoint commit and lost acknowledgement, actual worker
read-before-result crash, actual listening-backend process crash/restart, unrelated-process
survival, changed/replaced/missing/hardlinked/outside files, malformed/oversized/transcript
injection, model identity change, memory forgetting, version/attempt limits, stale/forged
approvals, mutation/command denial, concurrent single-consumer admission and rollback.
Backup/restore fixtures preserve nonempty checkpoint data; migration4-to5 failure rolls
back without rewriting history. Retention snapshots include checkpoints and refuse
cross-conversation source/resume references. Deleting the conversation cascades records.

Workspace supplies collapsible selected-file/question controls, deferred pause status,
recorded project/source metadata and explicit resume. Coding tools scroll independently
from chat controls. The900px rendered flow performs actual backend restart, opens saved
task history and resumes with read-only permissions even after UI tool access changes.
Earlier reads/planning are not repeated in the resumed worker. Final screenshot reviewed;
inference/native IPC are fixtures, while actual APIs, SQLite, ownership, workers and
file observations execute. User guide: docs/inspection-checkpoints.md.

Retained failures: version4-only test assumptions and an empty new-table restore fixture
were updated while preserving rollback/nonempty-table assertions. Final review reproduced
an image-limit ordering regression in the Agent refactor, restored validation before
planning and added a regression test before rebuilding. The earlier619-test run is retained.
The first packaged matrix had47 passes/1 failure: killing a launcher caused graceful
cancellation rather than a backend crash. The corrected test identifies exactly one
listening process in its owned tree, kills that runtime and keeps the interrupted assertion;
the unrelated canary survives. No global/name-based process kill or safety bypass was added.

Managed1909 interrupted final record writes after tests completed. Resumed access verified
IMPLEMENTATION.md was intact and completed parity/records without rerunning finished suites.
No account/ACL/security changes occurred. Existing Ollama remains unreachable here
(read-only URLError probe), so actual-model revalidation/message-export and semantic/native
gates remain open. P2-01 closes at its supported checkpoint scope; F06 external-state/CLI
work remains separate. Evidence: .runtime/p2-01-checkpoints/validation.json and after.zip.
Next increment: P2-02 pinned read-only local stdio MCP integration; SDK is not installed,
so inspect compatibility and ordinary dependency availability before changing functionality.

## P1-06 B4 manual conversation retention (verified 2026-10-25)

- [x] Audit authoritative B4/F12 contract, current single-chat cascades, memory epochs, ownership and settings lifecycle.
- [x] Review SQLite transactions/foreign keys/progress-handler documentation; snapshot before edits.
- [x] Implement configurable last-activity age/recent/batch policy and bounded exact-content previews, protecting current selection, active/pending work and unfinished goals.
- [x] Integrate strict authenticated preview/confirmation API and settings controls; no automatic deletion or filesystem pruning.
- [x] Verify atomic cascades, stale/expired/replayed previews, active-owner refusal, memory provenance/context reset and file preservation.
- [x] Run relevant source/default/packaged/rendered/build/lint gates; record actual evidence before closing B4.

Scope is stored conversations and their dependent SQLite records. Project files, backup
files and all generations remain untouched. Reviewed schema,64MiB/50,000-row/five-second
processing bounds and50-conversation batches fail without partial deletion. Policy saving
does not delete anything; each batch needs a new five-minute review and explicit confirmation.

Reuses the single-conversation deletion helper and existing memory provenance triggers in
one transaction. A bounded typed digest covers exact affected rows/attachment bytes and
kept memory-context recipients. Policy/store/preimage changes invalidate the consumed
review. Selection at preview, recent activity, unfinished goals, pending uploads and
nonterminal tasks are excluded. Any owned worker/cleanup, shutdown, pending restore
restart or emergency stop refuses retention. No schema version or dependency was added;
canonical DDL validation was factored from restore validation without weakening it.

Strict authenticated routes accept policy/protected IDs/opaque review, never paths or a
caller-supplied deletion list. Models cannot invoke retention tools. Models/settings adds
bounded previews, explicit keyboard-accessible confirmation, last aggregate receipt and
refresh of affected history/memory. Changing selection drops delayed previews. No approved
SQL transaction is presented as cancellable mid-commit; unknown results require refresh
and a fresh review. No automatic retry or blind rollback occurs.

Verification: final default598 tests /540 passed /58 skipped in232.144s; all90 targeted
checks passed without skips in30.687s. Initial source rendered scenario passed1/1 in5.067s;
the final expanded scenario, including actual owned-worker approval refusal, passed in
the45-check packaged UI/HTTP/runtime/socket/loop suite (208.435s,zero skips). Strict TS/Vite,
19 Node checks and Ruff pass. All25 inspected archived runtime entries match source.
Sidecar SHA256:61b69f58c723290bfa392f40dc5c48cd18f0b710f03d26b31640404e58dd5bb6.

Coverage includes denied/expired/replayed reviews, same-length title and same-size binary
edits, changed activity, second-delete failure rolling back the entire batch, row/byte/time
limits, unsupported schema/source relationships, nonempty journal/verifier/attachment/goal
cascades, memory forgetting/context invalidation, preserved kept transcripts and project/
backup/generation canaries. Actual HTTP restart preserves policy and aggregate receipt,
removes deleted events from new snapshots and refuses the old review. The900px rendered
flow covers Tab/Shift-Tab/Escape, focus return, stale review refusal, batch confirmation,
selection preservation, reload and delayed real preview delivery after switching chats.
The final screenshot was visually reviewed. Native IPC and inference are explicit fixtures;
real HTTP, SQLite, owned worker, approval and refusal paths execute.

The initial targeted command misspelled `tests.test_restores` as `tests.test_restore`;
its failed invocation remains in source-targeted-wrong-module.txt. Correcting the command
produced the90 passing checks; no application safety control/test expectation was weakened.
Evidence/snapshot: .runtime/p1-06-retention/validation.json and after.zip. Usage/limits:
docs/studio-retention.md. Export remains5,000 messages/8MiB without attachment contents;
private backups/SQLite free pages can retain deleted content, so this is not secure erasure.

User-provided normal-PowerShell browser/model output shows successful browser, structured
tools, GPU, vision, unified workflow and counter repair checks, with522 tests listed. Its
final unittest verdict/skip count was not included; it is not a complete current-checkout
acceptance record. A fresh read-only probe here still cannot reach existing localhost
Ollama (URLError); no service startup/restart, model download or permission change occurred.
The separate message/export actual-model gate remains blocked. Current native installed
product and semantic acquisition gates remain open; prior successful model evidence stands.

B4 closes independently; P1-06 B2b/B2/B remain open on the actual-model UI gate. No configured
VM provider/image exists in project configuration; Get-VM/VBoxManage/vmrun are unavailable
on this session PATH and OS capability query is denied. This does not prove virtualization
is absent; P1-07 acceptance needs a supported, approved disposable VM setup, and is not
claimed. Next independent actionable increment: P2-01, one read-only repository-inspection
checkpoint at an acknowledged completed step boundary, with restart/precondition tests.
No pause/resume support is advertised before that increment is implemented and verified.

## P1-06 B3b2 restore activation and restart (verified 2026-10-24)

- [x] Audit API/Manager/native restart, event identity/selection, worker ownership and test assumptions.
- [x] Snapshot before changes; add API lifetime state ownership, fixed-generation startup routing and an authenticated-request drain gate.
- [x] Implement validated confirmed activation, fresh rollback, guarded selection publication and pending-restart enforcement.
- [x] Add backup selection/inspection and restore/rollback controls with native restart and stale UI/event reset.
- [x] Test ownership/contention, startup/corrupt selections, drain/deadline and publication/crash boundaries.
- [x] Run source/default/frozen/rendered/build/lint checks; record evidence before closing B3b2/B3b/B3.

The current database remains intact. Selection routes only to a generated app-state
generation after validation; no model/user destination is accepted. A backend owner lease
must be acquired before Manager recovery, preventing a duplicate server from reconciling
the first server's active tasks. B3b2/B3b/B3 close at the verified local-data recovery scope.

Final default584 tests:527 passed/57 skipped in215.135s. All79 targeted checks passed
without skips in26.321s; the later restored-agent worker regression passed1/1 in1.202s
and is included in the final default run. Source rendered restore passed1/1 in8.327s;
all43 final packaged UI/HTTP/runtime/socket/loop checks passed without skips in209.706s.
Strict TS/Vite,19 Node checks and Ruff pass. Twenty-four inspected archived runtime code
entries match source; sidecar SHA256:
be03836c66752ff52f2ab8afeb545d71055e37b1026831e233ff395fbc07e9fc.
The CLI benchmark is not bundled; its restored-generation idle guard is source-tested.

Actual coverage: fresh current rollback includes an admitted concurrent rename; new
requests refuse during drain/pending restart. Approved worker file publication and its
artifact/verifier/task records use selected state, leaving original history intact.
Two actual runtime restarts restore then roll back; old event identity/cursors reset,
and new work needs fresh approval. Actual helper exits before/after atomic selection
publication reopen only the completed choice, without blind undo or tool replay.
Duplicate backends are refused before recovery, including different ports; OS process
exit releases the lease. Missing/corrupt/linked/changed state fails closed and startup
failure releases ownership without replacing original data.

The rendered900px flow covers inspection, keyboard Tab/Shift-Tab/Escape, confirmation,
two real backend restarts, settings/history/attachment recovery, unsent-draft clearing,
and held real old inventory/preferences replies. Old replies cannot replace new state.
Final screenshot was visually reviewed; spacing/wrapping use existing dark-mode styles.
Native IPC and inference in this harness are explicit fixtures. Installed WebView/native
clipboard/picker/installer and actual-model quality are separate gates, not certified here.

Retained failures were fixture issues: locked-byte read expectations, seeding waiting on
a terminal row, misplaced bridge handler, existing view-preservation navigation, and not
waiting for new-conversation selection before upload. Assertions/setup were corrected;
production safety controls remain intact. Managed1909 interrupted closure; resumed access
confirmed43 passing packaged checks and allowed the missing worker regression to run.
No account, ACL, admin or security-policy changes were made. An existing Ollama tags probe
remains unreachable; message/export real-model UI and semantic acquisition remain blocked.

Limits: private unencrypted copies;20 backup entries/five generation entries/512MiB caps;
cooperative deadlines do not bound hung OS I/O. Active generation directories contain live
data and are retained. Trusted direct Python integrations are not OS isolation. Unknown
publication outcomes require restart/inspection; no automatic fallback to an empty store.
Evidence boundary: .runtime/p1-06-restore-activation/validation.json and after.zip.
Next independent increment: P1-06 B4 explicit retention preview and confirmation, preserving
active tasks, project files and memory provenance. B2/message model and native gates stay open.

## P1-06 B3b1 restore preparation (verified 2026-10-24)

- [x] Inspect current SQLite storage/migrations, backup publication, auth, UI boot/event identity and native restart lifecycle.
- [x] Review SQLite online-backup, read-only URI and trusted-schema documentation.
- [x] Snapshot before changes; add strict confirmed backup-ID/hash preparation into fresh fixed app-owned state.
- [x] Validate reviewed schema before mutation, retain original data, renew restored store identity and create rollback snapshot before ready marker.
- [x] Add positive/negative preservation, hostile schema, crash/failure, ownership, bounds and actual HTTP tests.
- [x] Run source/default/packaged checks and record actual evidence before marking the component complete.

This is the preparation component of B3b. It leaves the current database/Manager/UI active
state unchanged and returns activated:false. B3b2 must add explicit activation/restart,
safe routing/rollback UX and process/crash/UI gates. B3b/B3 stay open until then.
No new dependency, external service, tool permission or model-generated destination.

Final evidence:559 default tests,503 passed/56 skipped in214.716s. All54 targeted
restore/backup/migration/history checks pass without skips in15.538s;18 final packaged
HTTP/runtime/socket/loop checks pass without skips in48.389s. Ruff passes; the one test
flattened for lint passed again in0.155s. Frontend source and built assets are unchanged
from B3a's passing TS/Vite/19 Node/rendered gates; parity is checked in the evidence script.
Final sidecar SHA256:a432125e6a29145c355b5ca15210a880e49248b0ca2f5509afa9555f1e89123a;
all21 inspected archived code entries match current source.

Preservation exercises every required nonempty table, binary attachments, memory, goals,
verifiers and journal rows, changing only the restored store identity. Current/newer data
survives in both active state and the rollback snapshot. Exact hash/descriptor identity,
strict auth/origin/confirmation/no destination, owned approval waits, stop/shutdown,
corruption/future version/FK/schema and hostile trigger/view/index cases fail closed.
Legacy v0 upgraded schema remains compatible. Actual helper exits before rollback and
before ready leave unaccepted drafts; subsequent work preserves those leftovers. Failed
marker/rollback, concurrent source change and unknown cleanup entries preserve current data.
Real HTTP and ordinary restart prove that preparation does not activate or replay anything.

Review strengthened standalone copying with checked file descriptors before SQLite parses
the private stage; the substituted-handle regression fails before foreign data is read or
parsed. Earlier558-test/18-packaged passing runs and sidecar were retained separately,
then final default/build/packaged gates reran after the application-source change. Final
Ruff-only test formatting was verified with its affected test. No failed check is hidden.
Evidence boundary: .runtime/p1-06-restore-stage/validation.json and after.zip.

An existing-service localhost tags probe is still unreachable; the separate message/export
actual-model gate stays blocked. No owned Ollama restart, ACL or security-policy changes.
B3b1 alone closes. Next: B3b2 confirmed activation/current-state routing, restart and rollback
UX, event/selection reset and crash/rendered acceptance. B3b/B3 remain open.

## P1-06 B3a consistent Studio backup (verified 2026-10-24)

- [x] Inspect Store/migrations, Manager admission/ownership, authentication, file publication and UI settings.
- [x] Review official Python Connection.backup and SQLite online-backup/integrity documentation.
- [x] Snapshot before changes; implement confirmed fixed-destination backup with30-second/
  512MiB/20-entry bounds, link refusal, exclusive publication and read-only validation.
- [x] Add Models & settings backup confirmation, private-data notice and hash/size result.
- [x] Add positive/negative preservation, WAL, permissions, timeout and actual HTTP/UI tests.
- [x] Run appropriate source/default/frozen/UI/build/lint checks and capture source parity.

Existing working components are reused: Python sqlite3, schema definitions, Manager lock,
path policy, session authentication and native modal. No dependencies or tool grants added.
Backup refuses any owned worker (including cleanup/storage), shutdown and emergency-stop
latch. It copies only the database; it cannot accept a destination path or restore anything.
B3b restore and B4 retention remain separate, unchecked work. B3 is not complete.

Evidence: default544 tests,488 passed/56 skipped in207.617s. Final targeted39/39 pass
without skips in9.611s; source rendered backup1/1 in4.049s. All39 rebuilt packaged
UI/runtime/socket/loop checks passed with zero skips in174.220s. Strict TS/Vite,19 Node
checks and Ruff pass. Twenty archived code entries match current application source;
sidecar SHA256:9c38b8976d814651419a84eff5d205e9219de673c098ba9b34c8b84357bd3d20.

Preservation compares every table, including actual nonempty verifier/journal/memory and
binary attachment rows. Committed WAL data survives independently; uncommitted changes
are excluded. Negative tests cover strict confirmation/auth/origin/no destination authority,
owned approval waits and cleanup/storage, stop/shutdown, bounds, incompatible schema/
identity/history/foreign keys, hardlinks, concurrent calls, late filename conflict and
unknown staging preservation. The rendered scenario saves only after confirmation, checks
the resulting SQLite/hash, then proves actual worker ownership refuses another backup.
Model/native IPC are explicit fixtures; no real inference or native installation claim.

Final test review moved verifier creation before task completion and explicitly requires
every preserved table to be nonempty. Production late-result rejection stays intact.
The39 targeted checks were rerun after this test-only correction; application/frontend
source is unchanged from the passing full regression, source UI and packaged gates.
Original approval-signature and action-label fixture failures remain recorded. Managed
1909 blocked closure temporarily; access recovered without account/ACL/security changes.
Evidence boundary: .runtime/p1-06-backup/validation.json and after.zip.

Only B3a closes. Backup files are private/unencrypted and a crash can leave an unaccepted
partial entry; cooperative deadlines do not bound a hung host disk call. Validated restore,
rollback/restart acceptance and retention remain missing. Next increment: B3b.

## P1-06 B2b task-history paging (verified 2026-10-24)

The message/export actual-model gate is externally blocked and remains open, with its
verified source/protocol evidence and two actual-UI failures preserved. Task-history
read/navigation is independent and can be verified without model availability.

- [x] Inspect current TaskHistory, Manager.tasks, snapshots, App selection and history API; snapshot before edits.
- [x] Add50-row task-page controls and bounded global activity metadata, always including owned worker slots outside the latest page.
- [x] Preserve legacy/tasks compatibility; add authenticated single-task metadata and snapshot metadata projection.
- [x] Pin selected older task metadata across refresh/reconnect; include retained cleanup/storage states in global stop and activity presentation.
- [x] Add positive/negative scope/auth/projection/owned-active tests and real UI traversal beyond200 tasks with approvals, selection and reconnect.
- [x] Run source/default/frozen/rendered checks, TS/Vite/Node/Ruff; record actual evidence and remaining model/native blockers.

No execution, model-context, permission or schema changes. Historical pages stay selected
during global updates; latest pages refresh when idle. Metadata excludes result blobs;
all diagnostic/journal inspection stays behind the existing authenticated endpoints.

Verification: default532 tests,477 passed/55 skipped in201.128s; targeted source47,
44 passed/3 skipped in30.064s. The three skips require real Studio inference. All38
packaged UI/runtime/socket/loop checks passed without skips in167.695s. Final source
task-history UI passed1/1 in13.647s. Strict TS/Vite,19 Node checks and Ruff passed.
Final review extended default activity selection to retained cleanup/storage owners;
explicit historical selection and conversation boundaries still win. Three affected
packaged task/scoping/keyboard scenarios passed after that frontend-only correction.

The actual251-row rendered fixture traverses six pages, opens the oldest run, reconnects,
keeps a backdated owned task visible globally, denies approval and emergency-stops another
real worker. A held post-deletion404 cannot repin the deleted chat or display a stale error.
API tests deny reads of tasks.result while metadata endpoints succeed; legacy/tasks stays
compatible. UI inference/native IPC use explicit fixtures; REST/SQLite/WebSocket, workers,
denial and stop execute. The two-owned-slot unit fixture tests projection, not execution.

Sidecar SHA256:2f692f89d42b8db0b29e45592a86fb8c26c33412e8cf3826fee880f02b3362f6;
all19 inspected archived code entries match source. Logs, final source hashes and boundary
snapshot: .runtime/p1-06-tasks/validation.json and after.zip. Retained initial UI-oracle
failure checked an absent alert incorrectly; the corrected assertion requires zero matching
Resource-not-found alerts. No production failure was hidden. Managed1909 access prevented
closure temporarily; ordinary workspace commands now work, without account/security changes.

Only the Task-history child checkbox closes. Message/export actual-model UI remains blocked
by model readiness/manifest access and its two failures remain recorded; B2b/B2/B stay open.
Native installer/OS isolation/semantic model acquisition remain separate gates. Next safe
independent increment: P1-06 B3 consistent backup, then validated restore.

## P1-06 B2b message paging and complete export (verified; live gate recovered 2026-10-25)

- [x] Inspect all message fetch/replay/submission/export consumers and memory source selection; snapshot before edits.
- [x] Add authenticated complete-transcript Markdown export with one SQLite read snapshot and explicit5,000-message/8MiB refusal limits.
- [x] Replace automatic full-message GETs with50-row page windows and older/newer/latest controls; preserve older browsing during live updates and reset on explicit new submission.
- [x] Keep export independent of visible page; never silently export only a page or bypass size limits.
- [x] Add auth/scope/limit/snapshot/epoch export checks and rendered multi-page navigation/live refresh/selection/stale response/download checks.
- [x] Run source/frozen/default regressions, TS/Vite/Node/Ruff; record actual evidence and remaining task-history paging. Historical failed gates below are retained; later current-source/model acceptance above closes this final requirement.

Only message navigation/export are in this increment. Task history/global active/approval
paths and backend model-context/epoch rules stay intact. No embedding integration or
automatic ingestion is introduced. B2b/B2/B remain open until all required components pass.

Implemented fixed50-message windows with older/newer/latest navigation, selection/request
guards and reconnect/live refresh that preserves older browsing. Explicit submissions
return to latest. Export reads the full visible stored transcript independently of the
window (including pre-forgetting text) in one snapshot, with hard refusal before any
download beyond5,000 messages/8MiB. Attachment bodies are excluded. Supporting goal/
attachment existence checks now use metadata instead of loading the full transcript.
Inspecting one old attachment now filters requested IDs in SQL before reading blobs;
the new metered100-attachment test verifies only the selected blob row is materialized,
with foreign/duplicate/empty selection negatives. Existing scope/maximum-four rules stay.

Initial source export/history16 checks passed3.421s; final broader source gates are
running after the attachment filter. Source rendered message navigation/export passed
1/1,zero skips,7.288s before that final Store optimization; full/frozen validation is
pending against the rebuilt final backend. TS/Vite and18 Node checks pass; Ruff passes.

Retained UI setup failures:125-message fixture correctly exhausted the default protected
8K context; test now selects16K using normal settings without changing guards. The denial
oracle now matches actual `Approval denied: create_file`. A fixture-only foreign task
result was not a transcript message; an explicit foreign-message canary is now seeded.
Playwright cannot wrap built-in list.append callbacks, so the test uses a lambda. Finally
the installed Response.finished helper leaves an unhandled target-close task; the test
now waits for the actual requestfinished event and paint, with no filtering/library patch.
All five original logs remain under .runtime/p1-06-messages/. The clean passing run has
no unhandled task/traceback. New delayed-page checks await finished delivery before
proving that a foreign selected transcript remains intact.

Final source targeted history/attachment/slash:37 total/36 passed/1 actual-model attachment
check skipped,11.427s. Final default discovery:529 total/475 passed/54 skipped,208.677s.
The intermediate pre-blob-filter528-test run is retained separately (474 passed/54 skipped,
198.701s). Skipped checks are not passes. TS/Vite,18 Node checks and Ruff pass.

Initial final-sidecar suite:37 tests/36 passed/1 failed,184.654s. The scoped browser case
expired its unchanged30-second assertion while the real worker was still in browser_open;
there was no navigation result yet. It was not an observed message-page mismatch. Error1909
then prevented reading that trace; all original handles were collected to terminal before
stopping. Access returned on resume without account/ACL/security changes. The unchanged
packaged scoped scenario now passed1/1 in8.780s, including real browser results/decoded
PNG/approvals. No production fix or deterministic root cause is claimed for the earlier
browser-start delay. Retained log: frozen-first-browser-open-timeout.txt. Full packaged
revalidation and actual-model chat/slash UI regressions are next; component remains open.

Full unchanged packaged revalidation passed **37/37,zero skips,146.345s**. Both subsequent
real-Ollama UI scenarios failed the same shared selector: the export button tooltip had
been renamed. Inspected both complete traces (2 errors,114.029s) and restored the stable
`Export conversation as Markdown` tooltip. Limits remain in an accessible description;
the existing assertions were not weakened. Final strict TS/Vite build passes with JS
`index-Bi_5iNYE.js`/CSS `index-C9Ub0usI.css`. The18 inspected archived Python code entries
match current source; backend SHA-256
`e08537028865ea8586edbbabd656ec222516d1bfc50f6dd4fc019c86b7df5a5e`.
Actual UI2 and affected packaged UI3 are running after the label correction. The Python
backend did not change, so its529-test default/37-test packaged gates remain applicable.
No repeated default run is required for a tooltip/accessibility-description-only change.

Post-tooltip affected packaged cases passed **3/3,zero skips,23.635s** (message/export,
scoped browser/approval and keyboard/drawer). Real-model UI2 then failed **2/2,247.070s**:
both had no available model and an Ollama-missing notice, not the earlier tooltip error.
Direct local tags refused connections(10061). Exercised the existing authenticated owned
startup lifecycle with disposable state and root config: service starts, but exposes zero
models and repeatedly logs existing qwen manifest `Access is denied`. After20s readiness
failed; no further tests were started and the owned lifecycle closed. Existing services,
model files, credentials and ACL/security settings were not changed. Logs/readiness JSON
are in .runtime/p1-06-messages/. This is an external current-model gate, not a pass or skip.

All source/protocol/frozen message/export checks and18 code/source matches are verified,
but the corresponding completion checkbox stays open for actual UI2. A partial evidence
snapshot explicitly records the two failures and blocked dependency. Continue with safe
independent task-history paging; do not rerun long real-model UI waits without readiness.

## P1-03 B dependency audit — embedding acquisition blocked (2026-10-24)

With A's actual recall gate recovered, inspected F05/B's explicit approved-text and
evaluation requirements. The existing service lists only qwen3.5:9b, not an embedding
model. Official Ollama catalog confirms `qwen3-embedding:0.6b` (639MB); official Qwen
documentation describes1024-dimensional retrieval embeddings and query instructions.
Official `/api/embed` supports batched input and `truncate:false` for overflow refusal.
No embedding suitability, quality improvement or integration is claimed without measurement.

Attempted ordinary acquisition with the existing bundled Ollama0.40.7 in an owned
localhost server and new workspace-only `.runtime/p1-03-semantic/models` cache. Readiness
passed, but manifest pull failed with Windows socket permission denial (connectex10013)
to registry.ollama.ai:443. DNS resolved; this is not the earlier manifest-read denial.
Acquisition failed, not skipped/passed. Owned server/job closed; the existing user service
was not stopped, reconfigured or used to route around the managed network restriction.
No ACL/firewall/proxy/model changes, no automatic cloud fallback. Evidence:
`.runtime/p1-03-semantic/acquisition.json`, acquisition.txt and acquire_model.py.

B remains unchecked: no available evaluated embedding model, no chunks/vector index or
semantic score. A remains complete. Continue independent P1-06 B2b message/task paging.
Optional normal-session dependency recovery is documented in docs/project-memory.md;
no user interruption or permission bypass is required to continue the independent work.

## P1-06 B2b first UI component — conversation paging (verified, 2026-10-24)

- [x] Audit all App conversation consumers, selection/approval source names, search and existing UI tests; snapshot before edits.
- [x] Replace automatic full conversation-list GETs with50-row authenticated pages, explicit Older conversations, server-side literal search and loading/empty states.
- [x] Keep selected older metadata independently of search pages; invalidate stale requests and add authenticated single-chat metadata lookup for source navigation.
- [x] Verify real72-conversation UI traversal/search, delayed old responses, selected-chat pin, new/delete/rename/reload and existing approval/memory flows.
- [x] Run relevant source/frozen integration, TS/Vite/Node/Ruff and regressions; record evidence without closing B2 prematurely.

No message/task paging or export change in this component; they remain B2b requirements.
The metadata lookup exposes only id/title/created under existing authentication. Current
model/permissions and database schema remain unchanged from verified B2a. Initial TS/Vite
build passes; new rendered tests use the real backend and delay one real search response
to exercise request-ordering safety. No inference is needed for history navigation.

Final gates: **522 default tests / 469 passed / 53 skipped**,206.116s; **36 frozen
UI/runtime/socket/loop checks passed, zero skipped**,148.098s. Source history12 passed
in1.128s; final actual conversation UI1 passed in4.708s. Strict TS/Vite,18 Node checks and
Ruff passed. Both original long-running handles reached terminal exit0; no replacement
was started for an observation timeout. Account1909 then prevented new commands and final
documentation. Access returned on resume without account/password/ACL/security changes;
recurrence cause remains unproven. No skipped test is counted as passed.

Sidecar SHA-256: `9b834993cf1bf1ec42fa18744815409fc8ad8b9349406106621894166110f54b`.
All18 inspected code entries match current source, including history/API/migrations and
runtime entry. Final frontend JS `index-CTiJsFN1.js`. Evidence, hashes and before/after
snapshots: `.runtime/p1-06-conversations/validation.json`, before.zip and after.zip.
The UI fixture uses72 actual SQLite conversations and only delays delivery of a real
authenticated search response; no model is called. Existing inference/native IPC fixtures
in other rendered checks do not certify actual inference or native installed-product use.

The selected metadata ref survives search/page changes and refreshes after rename, so
older selected chats keep their actual title/transcript. New/deleted chats and reload are
verified without a full-list GET. Each automatic request loads50 rows; clicking Older
explicitly grows the loaded sidebar list. Loaded count is not a total database count.
Only this conversation component is complete; B2b/B2/B remain open. Next actionable work:
message/task history paging, selected-run/replay behavior and explicit export completeness.

## P1-06 B2a — bounded history API (verified, 2026-10-24)

Audit: Store.conversations/messages return every row; tasks silently stop at200. App
uses these legacy routes, so no paged UI is claimed yet. The smallest independent backend
component adds authenticated read-only `/history/conversations`,
`/history/conversations/{id}/messages`, and `/history/tasks`. Preserve legacy endpoints,
worker/model context, approvals and replay while introducing a verified paging contract.

- [x] Inspect Store/API/event/UI consumers, migrations and existing tests; snapshot before edits.
- [x] Add bounded keyset pages (default50/max100), scope/store-bound cursors, literal Unicode title search and metadata-only attachments/tasks.
- [x] Add index-only schema v4 with transactional upgrades; no user files or model context changed.
- [x] Add real SQLite/API ordering, >200rows, cursor rejection, scope/auth, migration/data preservation and query-plan checks; initial19 targeted passed,1.508s.
- [x] Verify actual source/frozen HTTP endpoint behavior, existing migration/regression/runtime/UI checks and lint/build gates.
- [x] Record backend component evidence; keep B2 open until explicit older-page UI controls and selection/replay integration are implemented and verified.

Keyset ordering uses `(created,rowid)` so equal timestamps keep insertion order and deleted
cursor rows do not require lookup. Cursors are bounded positions, not credentials; SQL uses
trusted table/column constants and bound values. Conversation/database/resource/search
mismatch fails safely. Pages are live views, not point-in-time backups: concurrent deletion
can shorten them and backdated/reused-rowid inserts may appear on a later page. Metadata
does not include attachment bytes or task result blobs. Model-history epoch filtering is
unchanged; visible transcript pages retain older messages. SQLite scrolling-window API:
https://www.sqlite.org/rowvalue.html#scrolling_window_queries. No new dependencies.

Final checks: **520 default tests / 468 passed / 52 skipped**, 206.244s; **30 source
history/migration/socket tests passed, zero skipped**, 19.387s; **35 frozen rendered UI/
runtime/socket/loop checks passed, zero skipped**, 139.264s. Ruff passed. No frontend
source or assets changed since B1's passing TS/Vite/18 Node gates; hashes were checked,
and the existing rendered UI reran against schema v4/new backend. No skipped test is a pass.

Rebuilt sidecar SHA-256: `fca4d2c8858c0902d919ff3ac0f33a46ad90c381d6a541b2c56463346a0b5fd0`.
All18 inspected code entries match source, including new history module, migration/API
and runtime entry. Evidence/snapshots: `.runtime/p1-06-paging/validation.json`, before.zip,
after.zip. Initial Ruff found three implicit string concatenations in new test query
definitions; parentheses corrected them without changing test semantics or disabling rules.
No runtime test failures. The new HTTP test exercises205 messages over three actual
requests and rejects a foreign conversation cursor and unauthenticated callers.

Only B2a's backend contract is complete. B2b desktop integration is next: first bounded
conversation sidebar/search/older controls, then message/task paging and explicit export
behavior. B2/B remain unchecked; legacy UI still loads all conversation/messages and
the first200 tasks. No installed-app, live-model readiness or UI performance claim.

## P1-06 B1 — keyboard dialogs and responsive activity (verified, 2026-10-24)

Audit: all six dialog types used styled sections with aria-modal but no focus containment,
Escape dismissal or reliable focus return. The activity panel was hidden below 1000px.
Reuse existing React/browser primitives and ActivityPanel; no new dependencies or backend
permissions. Native HTMLDialogElement.showModal supplies inert background and focus
containment; cancel maps to safe dismissal, and Escape denies a sensitive approval.
Approval has an explicit emergency stop so modal background inertness does not hide it.
Official API references: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog
and https://react.dev/reference/react-dom/createPortal (no portal dependency required).

- [x] Inspect source/tests and snapshot current UI before changes.
- [x] Add reusable native modal and migrate command, chat, capture, attachment, memory and action dialogs.
- [x] Expose selected-task activity in a narrow-window drawer; keep wide panel and global stop/approval boundaries.
- [x] Verify keyboard Tab/Shift+Tab containment, safe Escape, return focus, stacked approvals, 900px access and resize.
- [x] Run existing rendered scenarios, Node, TS/Vite, Ruff and default regressions; record skips honestly.
- [x] Record evidence and mark only this B component, leaving paging/backup/restore/retention open.

Final default discovery: **508 tests / 456 passed / 52 skipped**, 203.046s. Final frozen
UI/runtime/socket/loop suite: **34 passed / zero skipped**, 133.150s. All 18 Node checks,
strict TypeScript/Vite and Ruff passed. The final independent keyboard/visual run passed
in 7.533s; actual 900px workspace and activity captures were reviewed. It checks all six
dialog types, twenty forward/backward Tab steps per tested dialog, inert background,
safe Escape and return focus, live approval over an activity drawer, resize, explicit
keyboard approval, and emergency stop before a new file is created. Actual API/file
tools and frozen workers run; inference/native IPC remain explicit protocol fixtures.
This does not certify native WebView installation or clear the current model-access gate.

The backend did not change in B1: reuse the P1-06 A sidecar with SHA-256
`dc56bc6ee1baa739460a3e55711ab4ad22423e73432c8c744e0a070291fd0024`.
No dependency, policy, lockfile or account changes. Evidence/snapshots are in
`.runtime/p1-06-accessibility/`; A's closed evidence snapshot is preserved separately.

Diagnosed failures are retained: native Edge Tab reached browser chrome at the boundary,
so Modal explicitly cycles visible enabled controls. Test setup initially failed to await
asynchronous conversation creation (especially duplicate default titles); it now awaits
the increased row count and selected title. The emergency-stop fixture initially reused
identical existing file content, which correctly needed no write/approval; it now proposes
a distinct new file and verifies it never appears. No production approval rule or existing
assertion was weakened. First full frozen run: 33 passed / one setup error; final all34
passed. Managed error1909 recurred during observation; after resume the original process
handle was absent and its complete log proved all34 passed. No duplicate job was started
to replace an observation timeout. Root cause of recurring lockout remains unknown.

Only B1 is complete; P1-06 B remains open. Next: B2 bounded conversation/message/task
paging and older-page controls, preserving task selection and global active/approval state.

Fresh P1-03 model recheck still fails: no initial port11434 listener, then production
owned Ollama startup lists zero models and logs manifest Access is denied after readiness
wait. Log `.runtime/p1-03-memory/resumed-live.txt`; owned service closed by its lifecycle.
No model files, credentials, ACL or security settings changed. Continue independent UI work.

## P1-06 A — UI components and scoped activity (verified, 2026-10-24)

P1-03 A/B's current native-model gate is blocked separately; its implementation/evidence
is preserved below and the checkbox remains open. P1-06 A is independent: P0-02 event
recovery and P0-04 image/privacy dependencies are verified, schema discipline exists.
The dangling P0-06 dependency was checked against F12 and all P0 sections: that item does
not exist; native acceptance remains the explicit P0-05 gate, not a UI refactor dependency.

Audit: `App.tsx` owns chat/model/workspace/history/approval rendering. `taskEvents` includes
all conversations, activity state uses global active/approvals, and preview is a single
unscoped string. Existing EventHistory replay/privacy, CommandOutput, ContextStatus,
TaskJournal/Diagnostics and MemoryPanel are reusable. Initially presentation-only; final
frozen validation exposed the transport fault corrected below.

- [x] Inspect App, API/event/history contracts, existing UI scenarios and F12 acceptance.
- [x] Extract chat, model, workspace, task/history and approval rendering behind typed props.
- [x] Add validated activity projection and explicit selected-task/conversation scoping.
- [x] Associate transient screenshots with their task; clear on reconnect/store reset; never show another task's screenshot.
- [x] Preserve global emergency stop and clearly identified global approval delivery.
- [x] Add positive/negative selector and actual rendered conversation/task switching checks.
- [x] Run TS/Vite, Node, Ruff and existing rendered/frozen regression scenarios; record actual skips and native limits.

Acceptance: extracted views retain existing flows; selected conversation/task alone drives
activity/output/context/preview, unknown task IDs cannot leak into a view, malformed known
event payloads render safely, switching/reconnecting shows no stale foreign preview, and
approval/cancel remain functional. 900px/focus/backup/retention stay P1-06 B; native install
and current local-model access remain separate open gates. Baseline: 503 default tests,
453 passed/50 skipped; 28 frozen checks plus both final memory flows. Snapshot before edits:
`.runtime/p1-06-ui/before.zip`.

Implemented `ChatMessages`, `ModelsPanel`, `WorkspacePanel`, `TaskHistory`, `ActivityPanel`
and `ActionApproval`; App retains orchestration, original submissions, connection/replay
and permission endpoints. Selected task membership is checked against the conversation;
explicit selection, active/latest defaults and submission ownership prevent foreign state.
Activity/output/context use that task; the one transient PNG has an owner ID and cannot
cross selection. Snapshot/reconnect clears pixels. Global approvals still arrive while
another chat is selected, identify the source and offer navigation without granting it.

Event payloads are now `unknown`, not `any`. Typed display projections validate plans,
verifier observations, command deltas/readiness and approval identity/details/expiry;
malformed observations remain inert JSON, and live envelope ownership cannot be replaced
by payload fields. Both replay and live approval paths use the same contract. Existing
test counts/artifact evidence and no-independent-certification text remain visible.
TypeScript's no-emit project permits `.ts` imports so Node can directly exercise shared
contract functions. No policy, agent.toml, dependency or lockfile change. The server-only
loop correction described below is required by a newly observed Windows transport fault.

Initial verification: strict TS/Vite, **18 Node checks**, Ruff and default discovery
**504 total / 453 passed / 51 skipped**, 201.685s. The scoped rendered frozen scenario
passed (1 test, 8.215s): real Edge PNG independently decoded, successful browser tool
evidence, source-identified global approval while another chat stayed Ready/empty,
approved file creation/unittest execution, task-specific output/images and reload with
no restored screenshot pixels. Inference and native IPC use explicit protocol fixtures.

The full frozen UI/runtime/socket run found **4 failures in 30 tests**, 184.354s: all
four expected `Ready` after completion but received `reported`. On access recovery,
each trace was inspected: context compaction, both journal cases and diagnostics export
failed at this idle-state assertion. The UI now preserves Ready and shows the selected
task's terminal status in the selector; existing assertions are unchanged. The scoped
scenario also checks both labels. Final frozen revalidation below clears this failure.

The next 30-check frozen run cleared all four idle assertions but had one teardown
failure (29 passed / 1 failed, 126.398s): real streaming-output UI completed, then backend
stderr contained an unhandled Proactor `socket.shutdown` reset (10054). The local Python
3.12 source matches the traceback; official source confirms shutdown occurs before
close/detach without a local catch. An ordinary 40-client HTTP-reset probe passed before
the change, so it is not claimed to reproduce this intermittent failure on every run.

The Windows ASGI runtime now owns a Selector loop through `asyncio.Runner`; no global
event-loop policy is changed. Its existing listener is still localhost/exclusive and its
auth, WS delivery, lifespan/EOF, cancellation and tool policies are preserved. All tool
workers are fresh processes and keep default Proactor support for Playwright/subprocesses.
Non-Windows startup still uses Uvicorn's original run path. Windows Selector is limited
to 512 sockets, sufficient for the current single-task desktop backend; no new throughput
claim. Added actual TCP-reset/reusable-listener, loop ownership/default-worker-policy and
unrelated-error visibility checks. No exception filtering, stdlib patch, or weakened
no-Traceback assertion. Source/frozen runtime and browser regressions passed against the
rebuilt backend sidecar as recorded below.

Other retained failures: `scoped-ui-first-missing-browser.txt` records missing frozen
Chromium. The isolated test configuration now explicitly selects installed Edge, matching
the outer browser and existing image gates; no browser policy was weakened. A temporary
icon import typo was caught by strict TypeScript and corrected before passing builds.
Managed account error 1909 interrupted documentation/edits after test jobs finished;
both handles were polled to terminal. Access returned on resume with no account, password,
ACL or security-policy changes. The recurring lockout's root cause remains unknown.
Evidence directory: `.runtime/p1-06-ui/`. User-staged README content remains untouched.

Final gates: **507 default tests / 456 passed / 51 skipped**, 201.697s;
**33 frozen UI/runtime/socket/loop tests passed, zero skipped**, 129.079s;
**16 source transport/runtime checks passed, zero skipped**, 22.203s. All 18 Node checks,
strict TypeScript/Vite and Ruff passed. This includes existing chat, approvals, streaming,
memory, journal, diagnostics and context scenarios, plus selected-task switching and real
Edge screenshot/readback. Inference/native IPC are explicit fixtures in these UI tests;
they do not clear actual-model or native installed-product gates. No skipped test is a pass.

New backend SHA-256: `dc56bc6ee1baa739460a3e55711ab4ad22423e73432c8c744e0a070291fd0024`.
All sixteen inspected PYZ modules and the runtime entry code match current source.
Frontend assets include `index-BMbPzQq9.js`; evidence hashes and before/after snapshots
are in `.runtime/p1-06-ui/validation.json`, `frozen-identity.json`, `before.zip`, `after.zip`.
All earlier failure logs remain. The 40-RST probe also passed before the loop correction,
so the original intermittent fault is not claimed to have a deterministic reproducer.

P1-06 A acceptance is satisfied at its presentation/transport scope. P1-06 B remains open:
next independent increment is accessible keyboard/dialog handling and 900px activity
access, followed by bounded history paging and separately verified backup/restore/retention.
Current managed access recovered without account/security changes; recurring 1909 root
cause and P1-03 manifest access remain unresolved external limitations.

## P1-03 A — explicit project memory (verified; live revalidation recovered)

- [x] Inspected current migrations, Store, Manager, authenticated API, slash commands and desktop integration. No existing memory service; reuse SQLite, Policy, project identity and task supervision.
- [x] Add migration v3, explicit note/message provenance, bounded keyword search and project isolation.
- [x] Integrate untrusted retrieval and server-generated citations; invalidate model history after forgetting or source-chat deletion.
- [x] Add authenticated memory controls and desktop remember/search/confirmed-forget flows.
- [x] Verify 32-question recall@5, bounded-context recall, cross-project negatives, permissions, deletion, migrations, regressions and frozen rendered UI.
- [x] Record the earlier successful actual Ollama restart/recall and forgetting evidence, without replacing the new failure with that historical pass.
- [x] Revalidate actual model recall in the current managed environment: existing local service exposes qwen3.5:9b and passes restart/recall/citation/forget acceptance.
- [x] Record actual results and remaining limitations. ROADMAP A is complete; embeddings/file ingestion remain P1-03 B.

**Recovery closure2026-10-24:** after the user's normal-session validation, the managed
session independently read local `/api/tags` and reused its existing qwen3.5:9b service.
Actual memory acceptance passed **1/1,zero skipped,3.417s** in
`resumed-existing-service-memory.txt`: restarted Manager/new conversation recall the exact
saved color with parent-owned citation/source ID; confirmed forgetting removes retrieval
and prior model history. No service was started/stopped and no model files, parameters,
permissions or security controls changed. Current522 default checks (469 passed/53 skipped)
cover32/32 lexical/bounded recall,64 distractors,zero foreign IDs and provenance/deletion/
authority negatives. All36 current frozen checks include both memory UI flows; inspected
memory/control code in the rebuilt9b834993 sidecar matches source. Together these satisfy A.

Prior success/failure logs and original blocked snapshot remain unchanged; closure evidence
is separate (`closure-2026-10-24.json`). Existing-service access is verified recovery for
this gate; the owned-startup manifest-denial operation and recurring1909 cause remain
unidentified. B's embeddings/chunks/index invalidation still require their own evaluation.

Implementation uses existing SQLite, Policy, canonical directory identity, Manager lock,
worker/current-user-message boundary and authenticated Studio API. `studio/memory.py`
owns explicit note/selected-message snapshots, strict scope+ID reads/deletes and bounded
Unicode-normalized keyword retrieval. Migration v3 preserves v0/v1/v2 histories and
adds FK deletion propagation. No new dependency, model download or framework.

Notes never grant tool authority. The parent freezes retrieved source IDs and appends
citations independently of worker prose. Forgetting/source-chat deletion advances a
project context epoch; old model history and generated goal checklists are omitted from
later requests while visible transcripts remain. Source deletion and memory mutation
cannot invalidate an active worker snapshot. Bound conversations cannot cross projects.
Reviewed UI: explicit notes/message selection, source navigation, search and confirmed
forget; `/remember`, `/recall`, `/forget`. Details and limits: docs/project-memory.md.

Evidence already captured: initial full discovery **499 total / 451 passed / 48 skipped**,
192.225s; all **14 memory checks** including actual Ollama restart recall, 11.964s;
**28 frozen UI/runtime/socket checks**, 106.054s. Final focused memory/migration checks:
**22 total / 21 passed / 1 live test skipped**, 6.062s. The strengthened fixed corpus
has 32/32 recall@5 and 32/32 bounded-context recall with 64 same-project distractors and
32 foreign-project notes, zero foreign IDs. This measures lexical retrieval on these
fixtures, not semantic recall or overall model quality. Final explanatory UI rebuild and
rendered frozen memory scenario passed (1 test, 5.266s); Ruff passed. The final full
regression completed: **503 total / 453 passed / 50 skipped**, 188.568s. Ruff,
TypeScript/Vite and all 11 Node checks passed. Both final rendered frozen memory UI
flows passed (2 tests, 7.604s), including slash remember/recall, cancelled/confirmed
forget, navigation without a stale dialog, source-chat cascade and no inference for
explicit memory commands. No skipped test is counted as passed.

Frozen executable SHA-256:
`d8e501b12700aa97246b1d5a92372af41b93d57b3afe4d947efa9a9d5d2748ec`.
Sixteen relevant frozen Python module code objects match current source, including
Memory/Manager/Store/migrations/API, policy, inference/context and tool boundaries.
Evidence lives in `.runtime/p1-03-memory/`. This is a test backend artifact, not a new
Windows installer or native installed-app acceptance.

Execution was interrupted by recurring managed `CreateProcessWithLogonW 1909`. All
previously started jobs were polled to terminal and passed; no duplicate job was started
to replace an observation timeout. Normal managed access returned on resume. No account,
password, ACL or security-policy changes were made; recurrence cause remains unknown.
The combined recovery/root-cause checkbox below stays open. Final documentation and
evidence review resumed 2026-10-24. Earlier broad model corpus failures/native install/
OS-isolation gates remain unchanged. No automatic file ingestion, embeddings, chunk
invalidation or secure disk-erasure claim; those derived-index requirements belong to B.

**Fresh model dependency failure, 2026-10-24:** port 11434 initially refused connections
(10061). The production authenticated `/models/start` lifecycle was exercised in disposable
state: its owned bundled Ollama 0.40.7 started, but `/api/tags` remained empty. A first real
memory attempt failed admission (`Select an installed local model`), retained in
`live-initial-empty-models.txt`. A second bounded readiness probe waited for the configured
model and failed after repeated `bad manifest ... Access is denied` server diagnostics,
retained in `final-live.txt`. This is a current blocked gate, not a passed/skipped test.
The existing manifest and all eight referenced blobs were present and Python-readable;
the denied operation has not been identified. No manifests, blobs, model parameters,
credentials, ACLs or security controls were modified. Both owned service processes were
closed by the existing lifecycle; unrelated services were not terminated. The earlier
14-test actual-model pass remains valid historical evidence for the same backend code,
but does not prove the new managed-server startup works. P1-03 A remains unchecked;
P1-03 B also needs usable/evaluated local model access. Recovery steps are in
docs/project-memory.md. Next safe independent increment: P1-06 A UI separation and scoped
activity, whose protocol-fixture/Edge gates do not require the blocked native model store.

## Documentation access recurrence - 2026-10-23

- [x] Reproduced managed runner startup failure: CreateProcessWithLogonW error 1909.
- [x] Explicitly approved execution outside the sandbox can read the workspace.
- [x] Updated recovery guidance and this log through that approved execution route;
  exact written contents were read back and verified.
- [ ] Restore normal managed execution and establish why the lockout recurs.

Earlier recovery statements describe earlier probes only. No account unlock, password,
ACL, sandbox configuration or security-policy change was performed. No roadmap feature
or application acceptance criterion is marked complete by this documentation update.

## Continuous roadmap execution - 2026-10-23: P1-05 B context budget and compaction

P1-05 A is verified. Inspected all existing character guards, Agent histories, image
provenance, tools/schemas, worker events and actual model payloads. Current tool schemas
occupy 7,921 serialized UTF-8 bytes for Unified and 4,551 for Coding; they were not counted.
Official Ollama 0.40.7 sources confirm per-request truncate/shift controls; the debug render
endpoint returns rendered text, not a stable exact-tokenizer interface. Use an explicit
estimate and native no-truncation behavior rather than invent an exact token count.

- [x] Centralize prompt/schema/template/image estimates and full configured output reserve.
- [x] Add bounded extractive compaction preserving all system/user instructions, original
  images, call groups, schemas, observed outcomes and canonical verifier references.
- [x] Reject unfit protected context clearly; request no silent truncation or context shift.
- [x] Integrate numeric context notices into authenticated durable worker events and a
  conversation-scoped UI display; preserve stored conversations and approval boundaries.
- [x] Add boundary/Unicode/code/image, privacy, injection and semantic preservation tests;
  compare original and compacted seeded tasks with independent required checks.
- [x] Verify real model/workflows/rendered/frozen integration, regressions/lint/builds and
  record evidence before checking P1-05 B. Evidence: `.runtime/p1-05-context/`.

No model/global server/dependency/configuration change was needed for this increment.
**P1-05 B is complete** at the bounded estimate/extractive-compaction contract.

`context.py` replaces separate character guards with a shared request estimate: UTF-8
message bytes/3 plus 16/message, schema bytes/3, image reservation 512+ceil(pixels/1024),
template 256 and full configured output. The policy is explicitly approximate. It protects
system/user/image/tool-call context and compacts only eligible assistant/tool text, retaining
canonical verifier records and structured outcomes/paths/hashes. No stored conversation
or caller message is mutated. Preparation is bounded to 512 messages/4 MiB text/512 KiB
schemas/eight images and three excerpt passes. Native `truncate=false`/`shift=false`
protect against estimate misses; the supported verified API floor is Ollama 0.40.7.

Model/Agent/Manager/Worker use this boundary; the obsolete character helper was removed.
Worker notices contain only validated fixed categories/numbers and use existing durable
authenticated delivery. `ContextStatus.tsx`/App/style add last-request estimates, compaction
and block remedies scoped to the selected conversation. All original tool approval/scope,
image ownership, cleanup and terminal persistence behavior remains enforced separately.

Verification:

- **486 unique default tests: 439 passed / 47 skipped**, 188.381s, exit 0. Skips are not
  passes. Twenty-three new cases cover context, semantic pairs, live gates and rendered UI.
- **24 frozen UI/runtime/socket checks passed / 0 skipped**, 95.945s: all fourteen rendered
  workflows, runtime spawn and nine socket/authentication checks. Final PyInstaller build
  passed. Fifteen extracted frozen module code objects exactly matched compiled current
  source after access recovery. Frozen SHA-256:
  `fb6710cf3d4c53cdcb2c3c9476d4bd2162eb64cc81b65f458840080cc2fa396f`.
- Two new source-rendered scenarios passed, 8.603s: compaction notice/preserved history,
  conversation-switch isolation, and unfit output reserve preventing tools/generation.
  Rendered inference remains an explicit protocol fixture, separate from actual-model tests.
- Final actual-model suite: **4 tests passed / 0 skipped**, 57.765s. Native Ollama rejected
  oversized input without truncation; all six original/compacted semantic variants passed;
  real Studio compaction preserved history and verified a JSON artifact; autonomous counter
  repair observed initial 3 tests/1 failure, generated passing 8-test result, independently
  counted 8-test rerun and separate 6-test oracle, with seed integrity and Git diff review.
- Final paired native prompt counts: original 5920/5918/5911 versus compacted
  2292/2284/2274. Both arms used native context 16384/output 512; precompaction budgets
  differ to isolate supplied context. Required JSON values, canonical verifier ID, fresh
  exact approval, independent artifact hashes and unchanged source all pass. This is a
  small semantic gate, not a broad latency/model-quality improvement claim.
- Actual original-image/browser regressions: **2 passed**, 21.723s; attachment survival,
  latest screenshot context and cleanup retained. Full Ruff, TypeScript/Vite production
  build and **11 Node tests** passed. Earlier targeted stage: 48 passed / 3 skipped.

Failures were diagnosed and retained: an older positive fixture used fake base64 and was
updated to a real PNG; the paired harness explicitly enables existing create-file review.
Two early actual code-seed uncompacted baselines copied literal MARKER_VALUE rather than
counter_add_42 and were denied. Clarified field mapping identically in both arms; expected
values and evidence/approval oracles stayed exact. A negative test proves the literal-key
proposal remains denied. Failed logs remain beside the later passing results.

Windows 1909 interrupted new commands/file writes after full/frozen tests had started.
Polled both existing handles to exit 0 without restarting them. On user pause/resume,
normal managed access returned at 2026-10-24 02:41 UTC; verified source/log integrity and
completed the final actual-model suite and evidence recording. No account, credential,
ACL or security-policy repair was performed. Recurrence root cause remains unproven;
preserve the user's documentation-access recurrence note and unchecked diagnosis item.

Limitations: estimates are model-dependent and can over/under-count; native refusal is a
separate boundary. Protected user instructions, call arguments or images can still exhaust
context. Excerpts omit source details and are not a memory service or completion proof.
Only installed Qwen has actual-model acceptance here; earlier five corpus failures remain.
No new installer/native GUI or managed public-web/physical-desktop acceptance is claimed,
and frozen test artifacts were not activated as a new installed app. Preserved user's
187 staged README additions, configuration/locks, `.vscode/` and recovery documents.

See [context behavior and bounds](docs/context-budget.md). Next actionable increment:
**P1-03 A**, project-scoped remember/search/forget with keyword retrieval, provenance,
deletion and seeded recall/security checks; its P1-01/P1-05 dependencies are now satisfied.

## Continuous roadmap execution - 2026-10-23: P1-05 A inference admission and options

P1-04 is verified. Inspected generation/streaming paths, task admission, worker options,
preferences/UI, metrics, protocol fixtures and evaluation runner. Confirmed streaming
uses configured max output while plan/tool calls hardcode 2048. Live Ollama is 0.40.7;
installed Qwen advertises completion/tools/vision/thinking and boolean thinking controls.
Reviewed official chat/show/thinking/structured-output documentation and upstream types.

- [x] Centralize strict generation option validation and payload construction across modes.
- [x] Add bounded identity/version/TTL capability caching, local-only admission, explicit
  supported thinking controls and an actual bounded schema compatibility probe.
- [x] Expose max output/thinking/residency settings in Studio preferences/task requests.
- [x] Preserve observed finish reasons and load/prompt/first-token/first-content timing; reject output
  truncation before tool execution or a successful task report, preserving partial chat.
- [x] Verify positive/negative/stale metadata, all mode payloads, Unicode/code/image cases,
  real model and rendered/frozen integration; retain skips and unrelated user changes.
- [x] Run regression/lint/build checks and update P1-05 A only after its criteria pass.

Output reserve, accounting and compaction remain P1-05 B. Existing configuration/lockfiles
are preserved; no dependency, global Ollama configuration or model replacement is needed.
Evidence directory: `.runtime/p1-05-options/`. **P1-05 A is complete** at this contract.

Changes: `inference.py` centralizes validated immutable options and a 32-entry/60-second
capability cache. Every admission rechecks local model tags/digest and server version;
remote/cloud models, missing completion/tool/vision support and unsupported thinking are
rejected. A bounded content-free schema probe precedes structured planning and confers no
tool authority. It uses 64 output tokens and no tools/images/user history; its time/count
are separate from task token statistics. Probe failure is cached only for the bounded TTL;
it is not proof of general model incapability. Metadata requests time out after five seconds.

`model.py` shares payload construction for streaming/non-streaming/plan/tool calls and
honors max output, thinking and residency. Only normal final `stop` completes a response;
length/unknown/missing final output cannot authorize tool dispatch or task success. Native
load/prompt timings and first streamed generated token/visible content timings are stored
without reasoning text; non-streaming first-token arrival remains unknown. Details are
bounded to 128 calls with explicit omitted counts. Store's existing metrics/preferences
JSON preserves the new fields without another migration.

Studio API/Manager/Worker expose and validate these options; endpoint/execution-limit
overrides cannot enter worker settings. Partial truncated chat is safely flushed through
the existing secret redactor, persisted and labelled incomplete. Frontend settings persist
through normal and slash requests; capability metadata is visible and per-call timings
are expandable below response statistics. TOML `thinking = "default"` maps to JSON null.

Verified evidence:

- **463 unique default tests: 421 passed / 42 skipped**, 181.189s, exit 0. Skips are not
  passes. Twenty-three inference/API/process/live methods plus one rendered scenario were
  added. Existing protocol fixtures now explicitly supply metadata/finish frames rather
  than bypass admission. Initial smoke failures were outdated fixtures and were fixed;
  the final full suite is green.
- Final current-source actual Ollama suite: **5 passed / 0 skipped**, 27.867s. Verified
  configured one-token `length` handling with native load/prompt/first-token/content data;
  real Studio file write/read with committed journal and artifact evidence; structured
  output with GPU residency; actual tool calling/result handling; vision. Qwen manifest
  digest remains `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`,
  `/api/ps` observed 5,862,210,928 bytes in VRAM at context 8192. This is integration
  evidence; the one-token run is not a throughput benchmark or broad quality evaluation.
- Source rendered settings acceptance: **1 passed**, 3.495s. Values persist and reach
  actual worker HTTP payloads; native timings and separate probe timing are displayed.
- Final PyInstaller backend build passed. **22 frozen tests passed / 0 skipped**, 85.825s:
  all twelve rendered profile/search/patch/command/background/diagnostic/journal/settings
  scenarios, actual runtime spawn and nine WebSocket authentication/protocol checks.
  Rendered inference uses an explicit protocol fixture; actual Ollama acceptance is above.
  Frozen SHA-256: `fc62329287cb8e6026d6ceaf75542879cd8eb8820600822df97a435cb48ce4ff`.
  After access recovery, nine frozen backend module code objects matched compilation of
  current source exactly, including inference, model, API, Manager/Worker and journal/storage.
- TypeScript/Vite production build (`--configLoader runner`), **11 Node checks**, and
  full Python Ruff passed. Earlier targeted stages also passed; final full logs and
  `.runtime/p1-05-options/validation.json` describe the authoritative snapshot.

The managed execution account subsequently locked with Windows 1909; commands and file
writes were unavailable and completion stayed unchecked. After the user's pause/resume,
normal managed access returned at 2026-10-24 01:33 UTC. Checked source/docs/log integrity
and reran the five current-source live tests before finalization. No password, account,
ACL, security policy, unrelated Python/Ollama process or native app was changed; do not
attribute recovery to an unperformed repair. The user's 187 staged README additions,
configuration/lockfiles, `.vscode/` and earlier recovery notes remain preserved.

Limits: only installed Qwen was tested with real inference; named thinking levels and
incompatible models use explicit protocol tests. Metadata/probes are compatibility hints,
not weight attestation, permission grants or quality certification. The existing measured
55/60 baseline and its five failures are retained; timing behavior now includes a separate
compatibility phase and is not a paired performance improvement claim. Exact token
accounting/reserve/compaction remains **P1-05 B**, the next actionable increment. Native
WebView2/install, managed public-browser and physical-desktop gates remain independent and
were not rerun. Frozen verification artifacts were not activated as a new installed app.
See [inference settings and limits](docs/inference-options.md).

## Continuous roadmap execution - 2026-10-23: P1-04 durable operation journal

P1-02 counted acceptance completed in the previous increment. Read current requirements,
Store/Worker/Manager, APIs, task diagnostics and storage/recovery tests. Existing traces
are observations, not a durable permission-to-dispatch boundary; existing ad hoc schema
changes have no numbered migration history. Preserve their data and public behavior.

- [x] Introduce numbered transactional migrations with legacy adoption, future-version
  refusal, atomic rollback and preservation of conversations/goals/attachments/cursors.
- [x] Persist run/decision/tool intent and fixed effect/precondition metadata; require
  parent commit acknowledgement before dispatch and persist observed results atomically.
- [x] Reconcile incomplete decisions/operations honestly on completion/restart; never replay
  actions or treat stored argument/approval hashes as authorization.
- [x] Add authenticated bounded read-only journal inspection and task-history recovery UI
  for inspecting uncertain work and opening a fresh instruction, without resume claims.
- [x] Test exits before intent/during action/after effect/after result, persistence and ack
  failures, approvals/privacy/deletion/migrations, rendered UI and frozen backend integration.
- [x] Run appropriate regression/build/lint checks; update roadmap only after all acceptance
  criteria pass. Evidence directory: `.runtime/p1-04-journal/`.

P1-04's smallest increment is complete at this Studio observation/reconciliation scope.
No new dependencies or configuration changes. Files changed: `studio/migrations.py`,
`journal.py`, Store/Manager/Worker/API, read-only construction in `safety.py`,
`TaskJournal.tsx`/App, seven migration cases, 23 journal/API/process/live cases, two rendered
scenarios and the independent legacy SQL fixture. README/review/gap/roadmap documentation
now links [the recovery guide](docs/execution-journal.md).

Verified results on the final production source:

- Default discovery: **439 unique tests, 399 passed / 40 skipped**, 164.317s, exit 0.
  Skips remain unpassed in this run. The earlier 434/438-test runs also passed before
  final guards/tests; the release log is authoritative for the final snapshot.
- Targeted journal/migration/supervision/observability: **72 tests, 71 passed / 1 skipped**,
  39.864s. Actual spawned workers terminate before intent, during execution, after an
  approved file effect and after committed result. Unknown effects are never replayed;
  completed results retain their verifier references through restart.
- Actual `qwen3.5:9b` Studio workflow: **1 passed / 0 skipped**, 7.368s on final source.
  Three decisions, two completed operations (`write_file`, `read_file`), exact byte readback
  and stored artifact evidence. This disposable exact-file approval grants no command,
  desktop or browser execution. This is integration evidence, not a broad model benchmark.
- Two new rendered Edge/source scenarios passed individually (4.104s and 3.902s):
  completed and restored-unknown journals, fresh inspection after a user edit, and opening
  a composer without submitting a task or replaying approval. The unknown UI state is an
  explicit persisted-state fixture; real process crashes are tested independently.
- Final PyInstaller backend build passed. The final frozen EXE passed **11 tests / 0
  skipped**, 34.618s: both rendered journal workflows plus nine real loopback WebSocket
  authentication/protocol checks. Source/frozen runs use disposable stores and the actual
  API/worker/tools; rendered inference is an explicit protocol fixture, separately from
  the real-model run above. SHA-256:
  `176838cc7b3c6094bdd38e195a4fb8968ff9da361be874ab3b5904db5c3dc9d0`.
- TypeScript/Vite production build, **11 Node checks / 0 skipped**, and full Python Ruff
  pass. The Vite build uses `npm run build -- --configLoader runner` in `desktop/`.

Corrections during verification: fixed a test's TemporaryDirectory/path mismatch and
import ordering; made inspection construct Policy without creating directories; rejected
a missing committed-result event before sending its acknowledgement. Regression cases
also cover changed preconditions, denied/fresh approval, transaction failures, lost or
wrong acknowledgements, cross-task/verifier references, deletion and malicious persisted
metadata. The PowerShell hash cmdlet was unavailable; Python hashlib confirmed the hash.

Limits: unknown means uncertain, even when present bytes match the proposal. Inspection
does not certify or overwrite outcomes; manual reconciliation informs a fresh instruction.
Only explicit Studio dispatches have this durability boundary; mandatory cleanup still
runs after storage failure, and standalone CLI retains its existing audit. Artifact
preconditions are bounded file-write/patch observations, not browser/desktop checkpoints.
No pause/resume, exactly-once external effects, OS isolation, backup/restore UI, or new
installer claim. Existing release/install artifacts were not replaced or activated; the
verified frozen test build is `.runtime/p1-04-journal/dist/agent-backend.exe`. Native
WebView2/install and managed public-browser/physical-desktop gates remain separate and
were not rerun here. Preserved the user's 187 staged README additions, configuration,
lockfiles, `.vscode/` and Windows recovery notes.

Next actionable increment: **P1-05 A**, validated inference options/capability cache,
finish reasons and timing. P0-04 and the measured P1-08 baseline satisfy its dependencies;
P1-03 memory still depends on that capability/context work. The overall roadmap remains open.

## Continuous roadmap execution - 2026-10-23: P1-02 counted live acceptance

Previous increment completed P1-08 B. Fresh source confirms the remaining P1-02 gap:
the legacy counter fixture's `-B -m unittest` profile bypasses the already implemented
canonical count runner. No production behavior needs changing for this increment.

- [x] Align the fixture with the supported canonical profile; narrowly validate actual
  helper argv/content/private paths/nonce/cwd as well as the requested command and hash.
- [x] Require canonical structured initial failure, post-fix success and independent
  rerun counts, preserving the six-test oracle, seed integrity and diff requirements.
- [x] Test forged/missing/inconclusive counts and unsafe helper approvals; run existing
  verifier and safety regressions without weakening unsupported-profile behavior.
- [x] Run current actual-model counter acceptance; close A/B only if all criteria pass.

Verified: **29 targeted tests, 28 passed / 1 skipped**, 21.455s; Ruff passed. Four new
cases cover LF/CRLF trusted helpers, forged requested-versus-actual execution, unsafe
paths/hash/nonce/body/hardlinks/raw fallback and false console success with absent,
inconclusive, zero or skipped structured evidence. Initial approval code incorrectly
compared LF source with Windows CRLF bytes; fixed to two exact trusted encodings.

Actual `qwen3.5:9b` counter check: **1 passed / 0 skipped**, 23.628s. Structured initial
counts: 3 tests / 1 failure, before any model edit. After repair: 8 tests passed; separate
counted rerun: 8 passed; independent semantic oracle: 6 passed. No skips/errors/expected
failures in passing records. Seed tests stayed unchanged, artifact readbacks passed and
Git diff was reviewed. Machine records are revalidated independently of model/console
prose. `live-evidence.json` preserves the fixed records alongside the full local log.

Final default: **407 unique tests, 370 passed / 37 skipped**, 149.320s. Skipped defaults
remain unpassed in that suite; the named opt-in was separately run successfully. Production
adapters, command recognition, inference/tool payloads, helper source and security policy
are unchanged. No runtime/UI/native build is needed for acceptance-helper-only edits.
No dependency/config/lockfile change. The user's staged README and recovery notes remain.

Requirement review: structured counts/failure-before-fix, exact artifacts, independent
tests/diff, spoof/zero/skip rejection, conflicting edits and cancellation/secret regressions
are verified at the P1-02 contracts. **P1-02 A/B are now complete.** Earlier historical
legacy-profile observations stay recorded; other test frameworks remain inconclusive.
General task certification, OS isolation, native installer gates and the five P1-08
baseline workflow failures remain separate limits. Next: **P1-04 numbered migrations
and durable operation intent/result records**, whose P1-02 dependency is now satisfied.

Evidence is recorded in `.runtime/p1-02-live-verifier/`. No source configuration,
model setting, approval API, production adapter or unrelated user change is modified.

## Windows 1909 recovery review - 2026-10-23

- [x] Confirmed fresh managed PowerShell commands run as ExampleUser\CodexSandboxOffline.
- [x] Read account status and machine lockout policy without changing either:
  account active; threshold 10, duration/observation window 10 minutes.
- [x] Workspace Python probe launched a child Python process, created/wrote/read
  a temporary file, asserted exact contents/output, and cleaned up successfully.
- [x] Documented account-lockout diagnosis and bounded recovery in docs/recovery.md.
- [ ] Establish the original failed-logon source or guarantee recurrence prevention:
  no matching 4740 events returned for the last two days; WMI inspection denied.
  Existing implementation notes already recorded recovery before this review.

The reported blocker is currently cleared. No password, ACL, sandbox configuration,
or security policy was changed; do not attribute recovery to an unperformed repair.

## Continuous roadmap execution - 2026-10-23: P1-08 B execution adapter

Fresh resumed source reads confirm the fix and existing logs. Verified final default:
**403 unique tests, 366 passed / 37 skipped**, 150.708s after baseline regressions; Ruff
passed. The earlier pre-baseline default was 401 tests, 364 passed / 37 skipped (148.001s).
The rendered
protocol matrix passed **60 workflows plus 8 deterministic safety cases**, 50.268s;
this establishes integration, not actual model quality. Earlier target run: 41 tests,
39 passed / 2 skipped, 6.043s. Evidence: `.runtime/p1-08-runner/`.

The account-lockout interruptions prevented earlier packaging/final evidence updates.
Access is currently restored; preserve the separate Windows recovery review above.
The exact original lockout cause remains undetermined. No account/policy/ACL repair
was performed by this implementation. Packaging and actual model checks follow below.

- [x] Built a real setuptools wheel containing byte-matching runner, fixture, scorer and
  corpus; isolated unpacked-wheel import/corpus checks passed. Wheel SHA256:
  `177e1de415a170092f792534a4f799104f5543a3e93065f4c992f5b889c027bb`.
  Evidence: wheel-build.txt, wheel-evidence.json and wheel-installed/ under the run directory.
- [x] Actual corpus completed, exit 0: **55/60 model samples passed (91.7%)**, **8/8 safety
  cases passed**, no critical/unknown effect observations; all sixty samples have metrics.
  Existing `qwen3.5:9b`, context 8192, temperature 0.1, output 2048. Native 23,781 tokens /
  301 calls, weighted **67.38 tokens/s**; all-outcome p50 **7.328s**, p95 **12.328s**.
  Inspected manifest/report/provenance/privacy; no oracle or failed sample was replaced.
  Root: `.runtime/evaluations/035ab655ccb04552989f2a46f650874a/`; CLI: live.txt.
- [x] Preserved all five failures: downloads 2/3 and missing-file recovery 1/2/3. Two
  recovery outputs lost the terminal newline; three tool-error causes remain unproven.
  Sanitized baseline fixture, exact-newline regression and immutable case references added.
  Final target: **43 tests, 41 passed / 2 skipped**, 5.900s; Ruff passed.
- [x] Five separate actual-model checks passed with no skips (33.917s): structured/GPU,
  tool-result handling, vision, unified browser/file task and autonomous counter debugging.
  Counter generated/rerun suites: eight tests; separate oracle: six. Important limitation:
  legacy `python -B -m unittest` fixture yields an inconclusive configured-test verdict,
  so this does not yet close P1-02 A/B's complete verifier/model gate.

Execution access recovered after the previous managed-account error 1909 blocked reads
and writes for three consecutive goal turns. Fresh source reads confirm search uses
Policy.path(write=True) for strict read-only link checks. The fixture adapter's path
override incorrectly required mutation grants for those reads; grants now belong to
create/overwrite/patch/download approval handling. Production path policy is unchanged.
The earlier full protocol result was 57/60, all three failures in scoped search; the
corrected matrix passes 60/60. Protocol fixtures remain separate from the actual score.

Previous goal turn made verified corpus/contract progress. Inspected current documents,
corpus/oracles, Agent/Tools, process/Job cancellation, browser approvals and fixtures.
Next component reuses these working boundaries; no application UI/inference rewrite.

- [x] Implement owned loopback/injection fixtures and exact disposable-workspace grants.
- [x] Collect actual Agent/Tools observations, independent effects/oracles/native usage.
- [x] Pin model/settings metadata; bound owned workers, cancellation and cleanup.
- [x] Preserve per-case failures/artifacts, run deterministic/live-protocol and regression
  checks; verify the actual corpus gate without treating fixtures as quality evidence.

Acceptance: actual fixture workflows/denials traverse production code, unintended effects
fail, hung/cancelled workers are reaped, metadata changes cannot pass, full matrix reports
missing/blocked cases accurately, and exports exclude raw tool/page/file/error/credential
content. **P1-08 B's stated corpus gate is satisfied.** Full general-task correctness,
installer/native acceptance, OS isolation and the five failed workflows remain limitations.
That legacy-fixture gap is resolved by the newer counted-acceptance section above.
The measured P1-08 baseline and its original observations remain unchanged.

## Continuous roadmap execution - 2026-10-23: P1-08 B corpus contract

Reviewed AGENTS and current roadmap/reviews, Agent/Tools/Coding/Policy/Browser/Model,
benchmarks/settings evaluations and acceptance/discovery tests. Existing verifiers and
benchmarks are reused/preserved. This first independent B component is complete at the
corpus/oracle/aggregation contract; it does not execute model tasks or establish a score.

- [x] Shipped version-1 definitions: **20 distinct model tasks** (8 coding, 5 browser,
  3 recovery, 4 injection) and **8 separate deterministic denials**. Three repeats/model
  case and one/safety case; all objective/fixture/oracle fields contribute to SHA256.
- [x] Bounded fixed schemas reject duplicate keys/IDs/objectives, unknown fields/oracles,
  missing state checks, overlapping Windows-case fixture paths, unsafe paths and oversized
  inputs. Independent oracles reuse strict stable Coding.read; raw-byte unchanged/text,
  strict JSON, static AST, real tool outcomes and fixture browser state are separate.
  Generated Python is never imported/executed. Missing browser data is inconclusive.
- [x] Fixed-field aggregation requires the full **60 model + 8 safety** matrix. Missing,
  blocked and inconclusive samples cannot establish a complete score. Failed oracles/
  unauthorized effects override claimed passes. Duplicates, mixed model/settings/weights
  identities, wrong corpus digest and invalid counters fail closed. Native usage coverage,
  weighted generation throughput and nearest-rank all-outcome p50/p95 remain distinct from
  verification. Protocol fixtures/deterministic-only inputs cannot establish model quality.
  Reports exclude prompts, paths/content, raw settings/logs/errors and launch-token fields;
  they explicitly provide no attestation. This is not a privileged evidence authority.
- [x] **20 new tests**: all manifest cases have positive and negative oracle subtests;
  exact raw-byte preimages, AST nonexecution, missing observations, thresholds, incomplete
  matrices, false passes, identities, metrics, privacy and sanitized CLI failures covered.
  Seven denial cases use actual production Tools with all approvals denied and verify no
  command sentinel, escape file, browser or desktop launch. The actual eighth browser
  case observes denied external_request plus zero POSTs; a click need not itself fail.
- [x] Final opt-in component run: **20 passed, 0 skipped**, 1.912s. Default component run:
  **19 passed / 1 skipped**, 0.397s. Broader benchmark/optimization/coding/discovery contract
  run: **31 passed / 2 skipped**, 11.216s. Skips remain unpassed.
- [x] Final default regression: **383 unique tests, 347 passed / 36 skipped**, 144.823s.
  Ruff and Git whitespace checks passed. A real setuptools wheel includes both module and
  matching corpus, and loads successfully from an isolated unpacked path. No new dependency,
  inference setting, tool schema or application UI/runtime change; frontend/native rebuilds
  were not applicable. The user's 187 staged README lines/config/lockfiles were preserved.
- [x] Added docs/agent-evaluations.md; updated README, roadmap and review evidence. Local
  before/after snapshots, test logs, probe, wheel and source hashes: `.runtime/p1-08-corpus/`.
- [ ] **Next actionable component:** bounded actual Agent/Tools workflow runner, owned
  loopback/injection fixtures, exact fixture-only grants, effect/cancel/cleanup guards,
  actual model/config/weights identities/native usage and preserved failures. The current
  CLI validates the corpus or aggregates supplied observations; it does not run tasks.
- [ ] **Live gate remains open:** fresh configured localhost tags probe timed out (URLError),
  recorded in model-probe.json. No actual 60-sample quality/p50/p95 measured result. No
  model/process/ACL changes, re-downloads, native/install acceptance or OS isolation claim.

Limits: strict AST equality is a narrow static contract and can reject correct alternative
implementations; generated unittest files are not executed by this corpus. Existing P1-02
coding-test acceptance still applies. A caller can fabricate offline observations/provenance;
only actual runner evidence can support later capability claims. P1-08 B stays unchecked.

## Continuous roadmap execution - 2026-10-23: P1-08 A local observability

Reviewed AGENTS/roadmap/review documents and actual Agent, metrics, Worker/Manager, Store/
replay, APIs and Task history/tests. Existing task UUIDs/native usage/durable events are
reused. P1-08's completed-verifier dependencies are satisfied; P1-02 model gates stay open.

- [x] Bounded version-1 content-free spans identify run/parent/decision/tool/approval and
  verifier links. Studio covers run/plan/model/tool/approval/cleanup and shortcuts; Agent
  tracing is opt-in. Manager validates ordering/identity/timing/verifier ownership. All
  22 tool schemas/inference payloads are unchanged; no execution-policy expansion.
- [x] Worker/model/tool-active/approval/cleanup timing uses monotonic observations; nested
  approval unions avoid double-counting. Planning is inclusive. Existing native counters
  are reused; missing counters/durations remain unknown. Caps: 512 spans/1,024 events,
  explicit drops; records are not task certification, checkpoints or approval authority.
- [x] Authenticated read-only diagnostics use bounded consistent SQLite reads and task/kind
  index. Allowlist excludes chat/tool/file/approval contents, paths, names/URLs and errors.
  Identifier/requested-setting hashes are not weights/applied-setting attestation. Exact
  launch credentials are removed on collision. Legacy/malformed/capped data is partial.
- [x] Task history loads timing/outcomes/verifier status, span inspection and actual JSON
  download. Stale generations are ignored and trace noise excluded from legacy activity.
  Unfinished terminal spans are interrupted with unknown duration, not running/success.
- [x] **17 new cases pass**: correlation/registry privacy, nested timing, taxonomy versus
  false prose, interruption/budgets/ordering, native/malformed metrics, credential collision,
  auth/missing/deleted task, read-only export and three actual Worker cases: approved write,
  failed unittest, cancelled approval. Reopen retains evidence and no private canary exports.
- [x] **70 targeted checks passed**, 38.898s, including lifecycle/startup/verifier regression.
  Final default: **363 unique tests, 328 passed / 35 skipped**, 142.349s; Ruff passed.
  Final TypeScript/Vite passed (2.37s); eleven Node checks passed. Test-only lint fixes
  preserve nested timing semantics; skipped checks remain unpassed.
- [x] **Nine rendered scenarios passed**, 30.895s in the source run. Diagnostic case loads
  actual data and downloads JSON, checking token/path/content/model-name exclusion. Final
  UI exposes outcome/verifier statuses immediately. Actual PyInstaller rebuild: **thirteen
  frozen-backend/UI/runtime checks passed**, 55.254s, repeating all nine on final UI/backend.
  IPC discovery is bridged and model replies are explicit fixtures, not native/model quality.
- [x] Added observability guide; updated README/roadmap/review evidence. Before/after source,
  logs, sidecar/hashes: `.runtime/p1-08-observability/`. Config/lockfiles/options/staging preserved.
- [ ] P1-08 B corpus/runner and repeated quality/p50/p95 remain pending; no >=90% score.
  Latest primary model probe has no listener; P1-02 model/native/NSIS gates remain open.
  No unrelated process stop, ACL/model-store change, model download or install acceptance.

Limits: Studio coverage only; CLI keeps existing audit. Latency includes instrumentation/
transport, omits pre-worker spawn/admission and can be a lower bound for partial data.
No hostile-code attestation, durable step graph, native GPU-stage profiling or task certificate.
Old binaries remain snapshots. A is complete at this contract; next safe increment is
P1-08 B corpus/runner, with real-model quality gated until the service is available.
Continuous execution remains active.

## Continuous roadmap execution - 2026-10-23: P1-02 owned background output/readiness

Read AGENTS/roadmap/review documents and inspected Coding.start/stop, process capture,
optional dependencies/configuration, Worker/Manager events, UI folding and tests. Background
starts previously spooled unbounded output and had no readiness contract. Retained existing
task lifetime, exact-command approval and command allowlist; user agent.toml was not edited.

- [x] Added BackgroundCommand ownership/lifecycle with shared bounded CommandOutput and
  extracted OutputPublisher. Both foreground and background retain existing 16,000-byte
  raw/display and 64-frame limits. Background monitor/reader/Job resources close on normal
  task completion, stop, cancellation, early exit, failed readiness and startup/delivery
  faults. Four owned background entries maximum; failed cleanup does not skip other entries.
- [x] Optional trusted `[readiness.<profile>]` accepts a bounded ASCII literal-loopback HTTP
  URL, explicit port, exact 2xx status, finite timeout/interval. Existing desktop-extra psutil
  verifies every listener on the port belongs to the owned process tree before HTTP. Missing
  dependency/invalid config fails before approval; unknown ownership never sends a request.
  No credentials/query/fragment, redirect, response-body read or proxy. IPv4 and IPv6 pass.
- [x] Configured starts wait for observed readiness or fail with diagnostics and owned
  cleanup. Unconfigured starts do not probe or claim readiness. command_status inspects
  only an existing owned profile and rechecks configured readiness. Duplicate starts require
  stopping the existing entry. No arbitrary URL/PID input or new public endpoint. Existing
  21 model-facing schemas are exactly preserved; command_status is the twenty-second tool.
- [x] Durable bounded background_status metadata shares the authenticated event path.
  Manager validates IDs/profile/PID, timestamps/configured URL/status and update budgets.
  UI shows lifecycle, last check and last-ready time as observations, with the latest three
  commands plus up to four active owned servers scoped to the selected conversation.
  Completion/cancellation does not turn a past readiness observation into current health.
- [x] A real slow-header test reproduced a timeout defect: socket inactivity alone allowed
  a 0.3-second startup budget to extend to 5.203 seconds. Added a bounded per-probe watchdog
  that shuts down only its HTTP socket, covering trickling headers in startup and explicit
  status probes. The regression passes unchanged. Startup/OS-inspection timing is cooperative;
  existing worker deadlines/emergency stop remain the outer boundary. No security bypass.
- [x] **20 new background cases pass**, including two actual worker workflows. Covers real
  IPv4/IPv6 HTTP, fresh status and failed checks, unconfigured/no probe, early exit/timeout,
  unrelated listener/no HTTP, redirect/slow/trickling response, invalid config and denied
  profiles/arguments, ownership inspection denial, bounded logs, duplicate/capacity refusal,
  stop during readiness, metadata validation/quota, failed monitor/status delivery, inherited
  child cleanup and continued cleanup after one failure. Worker cases start a real owned
  server, inspect status, run approved tests, then prove normal/cancelled server/process exit.
- [x] **58 targeted checks passed**, 21.314s. Final regression: **345 unique tests,
  311 passed / 34 skipped**, 134.371s; Ruff passed. TypeScript/Vite passed (2.80s); eleven
  Node checks pass, including active-server pinning and existing replay/retention tests.
  An initially missing test-fixture subprocess import was fixed; failing intermediate logs
  are retained. Optional desktop dependency/Windows-only tests retain explicit skip guards.
- [x] **Eight rendered UI scenarios passed**, 28.052s in the source run. The new cases show
  actual ready observations, subsequent approved tests, replay/reselection, normal cleanup
  and cancellation of both server/test process. Rebuilt the final PyInstaller sidecar after
  the watchdog fix; **twelve frozen/backend/UI/runtime checks passed**, 48.295s, repeating all
  eight UI scenarios on the final artifact. Native discovery IPC is bridged and model
  responses are explicit protocol fixtures; no native WebView/model-quality pass inferred.
- [x] Added docs/background-commands.md; updated streaming/profiles/README/roadmap/review
  evidence. Source snapshots, final logs, schema comparison, sidecar and hashes are in
  `.runtime/p1-02-background/`. Dependencies/lockfiles, user config and staging preserved.
- [ ] Broad P1-02 A/B model acceptance remains open despite implemented engineering parts.
  Fresh primary-Ollama tags probe returned 10061 (no listener); managed manifest denial is
  historical. Native WebView and NSIS/install gates remain open. No config/ACL/model-store
  change, model download, unrelated process termination or installer acceptance claimed.

Limits: ready is a point-in-time status/ownership observation, not program correctness or
continuous HTTP monitoring; command_status requests refresh it. Port ambiguity fails closed.
Known-pattern redaction only; hard worker death may omit terminal metadata. Windows Job
cleanup is not OS isolation or a portable POSIX subtree guarantee. Services end with their
task; no daemon handoff/persistence/checkpoint resume. Existing release artifacts remain old
snapshots. P1-04's broad P1-02 dependency is still open; next independent work is P1-08 A
observability, explicitly dependent on the completed verifier components. Continuous execution
remains active; skipped/model/native/install gates remain unpassed.

## Continuous roadmap execution - 2026-10-23: P1-02 bounded foreground output

Read AGENTS/roadmap/review documents and inspected foreground/background process handling,
the existing service-output redactor, Coding/test verifier, Worker/Manager, Store/replay,
event history and frontend/tests. Foreground commands retained output in temporary files
until exit; they had no live Studio path. Service diagnostics already streamed separately.
Selected only foreground output; background readiness remains the next complete increment.

- [x] Replaced foreground output temporary files with continuously drained merged pipes.
  CommandOutput decodes/redacts only a 16,000-byte raw prefix and caps displayed UTF-8 bytes
  independently. Excess output drains without storage. Incremental redaction precedes all
  worker frames; clipping cannot publish recognized partial credential bodies. Python child
  output is unbuffered. Existing shell-free argv, scoped cwd and approvals remain unchanged.
- [x] A trusted Coding sink covers configured foreground commands and the actual unittest
  verifier. At most 64 sequential deltas per command, with normal updates >=200ms apart,
  start/final metadata and deferred final tail. Manager validates identity, profile, part/
  byte budgets and terminal metadata before normal durable event storage. No new API tool,
  endpoint or dependency; all 21 existing tool schemas exactly match the saved baseline.
- [x] Windows commands own a nested Job Object, closing descendants inheriting stdout on
  completion, stop, timeout and callback/startup failure. Existing unrelated processes remain
  untouched. Partial sanitized output persists before completion/cancellation; no missing
  final frame or zero exit code can create passing test evidence.
- [x] Added a conversation-scoped latest-three command panel, plain-text rendering, exit/
  interrupted status, prefix/gap warnings, durable replay folding and duplicate suppression.
  Command frames no longer crowd the existing activity cards. Page reload opens a blank
  chat as before: selecting its persisted conversation restores output without rerunning.
- [x] Review caught a security regression before sign-off: applying display redaction to
  internal NUL-delimited Git configuration could hide later policy keys or collapse hashes.
  Bounded original parsing is now explicitly private to internal Git config/path checks,
  and raw mode cannot attach a streaming sink. Regression proves distinct secret-valued
  configuration hashes and rejection of helper keys following such a value. Displayed output
  remains sanitized. No policy relaxation was used to make Git tests pass.
- [x] **15 new streaming tests pass**, including two actual worker tests. Covers output
  before exit, real stdout/stderr and split Unicode/credentials, invalid UTF-8, large/no-newline
  output, raw/display/frame limits, final-tail integrity, stop/timeout, unrelated process
  survival, inherited-pipe children, callback/reader/Job startup failure, denial, structured
  test counts, transactional frame validation, durable restart and cancellation without a
  fabricated verifier. Fault harness now tracks the command child rather than taskkill.
  A Windows cleanup assertion was corrected to await actual bounded process termination;
  immediate PID-object disappearance is not equivalent to exit. A live 30-second orphan
  still fails the two-second child-exit bound. Prior failed logs are retained.
- [x] **83 targeted checks passed**, 46.532s. Final regression: **323 unique tests,
  291 passed / 32 skipped**, 130.973s; Ruff passed. TypeScript/Vite passed (2.65s); all ten
  Node tests passed, including replay/scope/gap/output bounds. The initial helper/component
  names collided under Windows TypeScript resolution; the helper is now commandHistory.ts.
- [x] **Six rendered UI scenarios passed**, 18.925s, including actual live output while
  tests remain gated, reload/reselection without duplication, escaped HTML/secret checks,
  cancellation and independent test-count cards. Rebuilt the actual PyInstaller sidecar;
  **ten frozen-backend/UI/runtime checks passed**, 39.637s, including these same scenarios.
  Native discovery IPC is bridged and model replies are explicit protocol fixtures; no
  native WebView or local-model quality pass is inferred.
- [x] Added docs/command-streaming.md and updated README/roadmap/review evidence. Before/
  after snapshots, final logs, schema comparison, sidecar and hashes are under
  `.runtime/p1-02-command-stream/`. Source/config/user staging were otherwise preserved.
- [ ] Background start_command still needs bounded output/readiness/owned cleanup work.
  Full P1-02 A/B acceptance remains open; a fresh primary-Ollama tags probe returned Windows
  10061 (no listener). Native WebView and NSIS/install gates remain open; no service/ACL/
  model-store changes, model download, unrelated process termination or installer pass.

Limits: known credential patterns only; prefix output, not unlimited terminal history.
Slow child buffering can delay output. After the event budget, remaining captured text
waits for final delivery. Hard worker death can omit final metadata; UI reports uncertainty.
The Windows process-tree checks do not establish OS isolation or portable POSIX subtree
cleanup. Existing release artifacts remain old snapshots. Next: background readiness within
P1-02 B; continuous execution remains active.

## Continuous roadmap execution - 2026-10-23: P1-02 reviewed patch sets

Reviewed AGENTS/roadmap/review documents and actual Coding, Policy, atomic publication,
ToolSpec, Worker/Agent evidence, approval UI and tests. Single-file atomic/version-bound
edits already worked; related-file review and whole-set preflight were missing. Reused
those primitives without introducing another framework, command endpoint or dependency.

- [x] Added `patches.py` and the Coding/Unified `apply_patch` tool. Up to eight explicit
  path/expected_sha256/text changes use raw-byte preimages (`missing` for creation), one
  diff/hash/size review and bounded whole-file credential redaction before diff generation.
  All preimages revalidate after approval and before any publication. Pending resources
  revalidate during execution; stale content/identity, new occupants, links, private state,
  duplicate/overlapping paths and oversized inputs/reviews fail closed.
- [x] ToolSpec now permits the explicitly registered bounded change-object array, validating
  unknown/missing/wrong-type nested fields before adapter dispatch. Existing 20 schemas
  exactly match the saved pre-increment snapshot. apply_patch is the only new schema/tool.
  Existing read_file text keeps universal-newline behavior and adds a stable raw-byte SHA-256
  for proposals; bounded read/fingerprint checks prevent mismatched byte/hash observations.
- [x] Each publication reuses existing atomic file/DACL behavior and artifact readback.
  Worker emits individual durable artifact observations; Agent retains them separately
  from prose. Incomplete publication returns written/uncertain/pending paths, preserves
  completed work and blocks automatic retry/continuation. No blind rollback. An ordinary
  set is not crash-atomic; stop/death can leave changes without a final set report.
- [x] **17 new patch tests** pass, including three actual worker cases: one review for two
  related edits followed by separately approved tests with two artifact records and one
  actual unittest result; denial and changed-preimage refusal. Direct tests cover exact
  Unicode/newline bytes, no-ops, stale hashes, identity replacement/delete, new occupants,
  path/hardlink/control refusal, shape/size limits, redacted review, immutable proposal copy,
  mid-publication conflict, failure after a real write, failed readback, no retry and stop.
- [x] **91 targeted tests passed**, 18.960s, across patch/tool/review/artifact/search/coding/
  agent regressions. The initial structural-test mock lost the handler signature; replaced
  it with an explicitly typed forbidden handler, preserving the strict registry check.
  Loop-variable fixture lint findings were fixed. No test or security validation weakened.
- [x] Full regression: **306 unique tests, 276 passed / 30 skipped**, 127.115s; Ruff passed.
  TypeScript/Vite passed (2.52s), seven Node checks passed. **Four rendered UI scenarios
  passed**, 12.883s; the new scenario inspects both proposed files before approval and
  verifies both actual writes and persisted artifact cards. Existing approval UI reused.
- [x] Rebuilt PyInstaller sidecar in `.runtime/p1-02-patches/dist/`; **eight frozen/backend/
  UI/runtime checks passed**, 29.922s, including patch review, actual spawned execution,
  evidence rendering and owned lifecycle/startup failures. UI inference replies are explicit
  protocol fixtures; native IPC discovery is bridged, so no model-quality/native UI claim.
- [x] Updated docs/patch-sets.md, tool profiles, README, roadmap/review evidence; source
  snapshots, logs and hashes are retained in `.runtime/p1-02-patches/`.
- [ ] B remains incomplete for bounded command streaming and background readiness. Full A
  still needs current real-model counter acceptance; latest listener probe returned 10061.
  Existing managed model-manifest, native WebView and NSIS/install gates remain open. No
  ACL/security-control change, unrelated process termination, model download or install pass.

Limits: create/replace UTF-8 files only; no delete/rename/binary patch. Proposed contents
total 64,000 bytes; preimages at most 64,000 bytes each; review diff at most 32,000 bytes.
Hash/readback observations do not certify program behavior or isolate hostile processes.
Unexpected process death still requires inspection; durable operation journals remain
P1-04. Existing release binaries are older snapshots. Next independent increment: bounded
command streaming in P1-02 B; continuous execution remains active.

## Continuous roadmap execution - 2026-10-23: P1-02 bounded repository search

Reviewed AGENTS and all roadmap/review documents, then inspected Coding/Policy, immutable
tool registration/profiles, authenticated file APIs and the Workspace UI/test fixtures.
File listing/readback already existed; bounded text search did not. Selected only the
first independently testable part of B, preserving its later patch/output/readiness work.

- [x] Added `repository_search.py`, shared by Coding.search, `search_files` and authenticated
  GET /search. Literal case-sensitive UTF-8 search; root/project/link/credential/state
  restrictions, emergency stop, explicit entry/file/byte/depth/time/match/output caps.
  Results retain original locations, observed SHA-256, bounded whole-file-redacted previews
  and incomplete/skipped evidence. No command, new dependency, mutation or approval bypass.
- [x] Workspace search form opens actual files through the existing scoped read API;
  query/project URL encoding, timeout/error display, scoped response-generation guards
  and incomplete-result status are implemented. No native picker functionality changed.
- [x] New Windows tests initially failed because DirEntry.stat reports zero link counts
  and identities. Replaced its cached metadata with path lstat, preserving real link and
  stability checks. All failures were rerun successfully; no assertions disabled.
  Initial UI expectation was corrected to the observed byte-output cap, which legitimately
  precedes 50 matches; the UI still must display explicit incomplete coverage.
- [x] **31 targeted tests passed**, 5.100s: 17 new search and 14 existing tool-contract cases.
  Includes literal Unicode/line/hash/no mutation, project boundaries, controls/credentials/
  internal state, hardlinks, binary/invalid text, changed-during-read omission, supported
  secret redaction, output and traversal caps, invalid inputs/stop, auth/profile denial,
  and an actual spawned worker executing the search tool with explicit model fixtures.
- [x] Full regression: **288 unique tests, 259 passed / 29 skipped**, 122.292s. Ruff passed.
  TypeScript/Vite passed (2.64s); all seven Node tests passed. Original 19 model-facing
  schemas exactly match the saved P1-01 source snapshot; search is the only new schema.
- [x] **Three rendered UI scenarios passed**, 9.286s: configured-test approval/denial,
  artifact-write evidence, and search/open-file/incomplete-output. Rebuilt the actual
  PyInstaller backend; **seven frozen-backend/UI/runtime checks passed**, 25.472s, including
  search, worker spawning, shutdown/port ownership and explicit startup failures. UI model
  protocol responses are fixtures, not real Ollama inference or native WebView validation.
- [x] Added docs/repository-search.md and updated profiles/README/review/roadmap evidence.
  Logs, rebuilt sidecar, source snapshot and hashes: `.runtime/p1-02-search/`.
- [ ] P1-02 B remains incomplete: reviewed patch sets with preimage conflicts are next;
  bounded command streaming and background readiness follow separately. Full A remains
  open for current real-model counter acceptance. Fresh port-11434 probe returned Windows
  10061 (no listener); managed model-store access denial is historical evidence. No service
  ACL changes, model downloads, unrelated process termination or new installer claimed.

Limits: eligible UTF-8 scope only; excluded inputs do not imply whole-repository coverage.
Checks are cooperative between filesystem operations, so blocked OS I/O can exceed the
three-second search deadline. Identity checks are not OS isolation or a whole-tree snapshot;
redaction covers known patterns only. Existing release binaries remain older snapshots.
Native WebView acceptance and NSIS download/install gates remain open. Continuous roadmap
execution remains active; next safe increment is reviewed patch sets within P1-02 B.

## Continuous roadmap execution - 2026-10-23: P1-02 artifact readback/hash verifier

Read AGENTS and the roadmap/review documents, then inspected Coding.write, existing atomic
publication/fingerprints, verifier validation/persistence, Worker/Agent evidence and UI/tests.
Preimage approvals and atomic publication were already implemented; post-publication
independent byte/hash evidence was missing. Preserved the existing publication mechanism.

- [x] Coding writes and no-op requests now perform policy-checked, bounded readback of the
  originally approved destination. A stable byte count/SHA-256 must match the proposed
  UTF-8 bytes to pass. Resource identity/metadata receives an opaque version digest for
  future references. Readback failures never repair, replay or undo a mutation.
- [x] Verification schema now supports artifact records alongside unittest records. Parent
  validation recomputes canonical verdicts; model-provided status cannot override a hash
  mismatch. Records contain IDs, bounded sanitized relative labels, sizes and digests, not
  file contents or raw filesystem errors. Existing atomic SQLite/event commit and authenticated
  read-only retrieval are reused; no new model-callable tool or endpoint was introduced.
- [x] Worker emits artifact evidence for write_file; Agent retains it separately from prose
  and treats failed verification as a failed observation. UI renders an Artifact readback
  card separately from Test run observations and states the whole task is not certified.
- [x] Exact-byte testing exposed an old newline no-op issue: text decoding normalized CRLF
  to LF before comparison. Write comparison now preserves original newline bytes, so a
  requested line-ending change receives the existing overwrite review and exact readback.
  Literal no-ops preserve file identity/mtime and do not request an unnecessary overwrite.
- [x] Thirteen new artifact cases plus eighteen test-verifier cases: **31 passed**, 7.384s.
  Covers Unicode/empty/no-op bytes, newline review, wrong/missing publication, unstable file,
  hardlink and outside-scope refusal, approval denial, invalid/forged metadata, secret labels,
  no content persistence, actual approved worker write, denial and authenticated history/deletion.
  The earlier no-test-evidence assertion now distinguishes artifact observations from unittest
  observations, preserving its prohibition on model prose inventing passing test evidence.
- [x] Full final regression: **270 unique tests, 242 passed / 28 skipped**, 121.129s; Ruff
  passed. TypeScript/Vite passed (2.61s); seven Node tests passed. Two actual rendered
  frontend/backend/approval/file/test scenarios passed, 6.086s. Their model protocol replies
  are explicit fixtures; no real inference is claimed.
- [x] Rebuilt the actual PyInstaller sidecar under `.runtime/p1-02-artifacts/dist/`.
  **Three frozen/backend/UI cases passed**, 13.474s: real approved file write/hash card,
  configured-test card/denial, and external Python tests with durable history across restart.
  UI fixtures explicitly select the external test interpreter for frozen execution.
- [ ] Full P1-02 A remains open for current real-model counter acceptance. A fresh prerequisite
  probe found no service on the configured Ollama port; the earlier managed manifest-access
  denial remains documented. No model was restarted, downloaded or reconfigured this increment.
  Native WebView/installer/NSIS gates remain open; skipped and blocked tests are not passes.

Requirement audit: observed byte agreement is established after successful publication or
no-op, existing review/scope/link limits remain, unexpected outcomes preserve concurrent
data, observations persist independently of prose and survive/restrict retrieval as required.
This is point-in-time evidence for coding writes, not semantic correctness, later-file
invalidation, hostile-process attestation or OS isolation. See docs/artifact-verification.md.
Both initial verifier components are implemented; full A stays unchecked for its remaining
model acceptance. Next independent increment: bounded scoped repository search in P1-02 B,
while the external model gate remains recorded. No search/patch functionality was added here.

Logs and source baseline: `.runtime/p1-02-artifacts/`. Previously produced packaged/release
artifacts keep their earlier source snapshots; this increment's checked sidecar is in that
evidence directory. Production installer readiness is not inferred. Continuous execution is active.

## Continuous roadmap execution - 2026-10-23: P1-02 first configured-test verifier

Inspected command execution, Agent evidence, Worker/Manager lifecycle, Store completion and
UI activity paths. Confirmed `/test` previously accepted exit 0 with zero discovered tests.
Selected the roadmap's explicitly permitted first single-verifier increment; full A remains
open. Reused stdlib unittest, existing approval/process/SQLite/event layers; no dependency added.

- [x] New `verification.py` supplies a small local runner for configured `{python} -m unittest`
  profiles. It records TestResult testsRun/failures/errors/skips/expected failures/unexpected
  successes through bounded structured metadata, not stdout parsing. Original discovery/module
  options are retained. The approval shows actual helper argv, requested argv and helper hash;
  changed reviewed helper files are refused. Other runners execute normally but remain
  inconclusive if this verifier cannot observe counts. No automatic command replay.
- [x] A passing observation requires exit 0, nonzero tests and no failure/skip/expected-failure
  outcomes. Zero-test `/test` is failed; skipped/custom/missing-result runs do not become passed.
  Agent evidence retains host observations separately from model prose. A model can still
  incorrectly report success, but that prose cannot create or override a verification record.
- [x] Testing exposed stale Python bytecode after same-size edits within one timestamp tick.
  The runner now uses a fresh cache prefix and disables writes; a seeded stale-cache regression
  proves changed source is tested. Existing caches are preserved. An early-exit test was
  corrected to use os._exit: unittest appropriately treats ordinary SystemExit during discovery
  as an actual test error. No failed assertion was removed to achieve a pass.
- [x] Separate `verifications` table stores fixed, validated numeric evidence and command
  hash only. Counts/status are revalidated in the parent; record plus event commit atomically,
  duplicate IDs are idempotent and terminal tasks refuse late observations. Records survive
  backend interruption and disappear on conversation deletion. Authenticated per-task GET
  exposes up to 200 latest records. There is no model-writable verification endpoint.
- [x] Worker emits trusted verification events; Manager persists/publishes them without
  mixing them into terminal-prose completion. UI shows test-run verdict/counts separately and
  states that the observation does not certify the entire task. Existing task status and
  goal-completion rules remain. No automatic project/goal verification is introduced.
- [x] Eighteen new deterministic/process/API tests pass: final targeted 18 passed, 4.842s.
  Includes real unittest pass/fail/zero/skip/expected failure, forged console success, abrupt
  exit, changed helper, cache invalidation, truncated output, unknown runner, denial, false
  model prose, SQL rollback/duplicate/restart/deletion, authentication, cancellation and
  seeded secret output absent from live/persisted data.
- [x] Full regression: **256 unique tests, 229 passed / 27 skipped**, 118.670s; Ruff passed.
  TypeScript/Vite passed (final Vite 2.44s), seven Node tests passed. Actual rendered
  UI/backend/approval/external-test check passed and validates the evidence card/API counts;
  its model-metadata fixture makes no inference calls and is not a real-model success.
- [x] Built a new actual PyInstaller executable in `.runtime/p1-02-test-verifier/dist/`.
  **Five frozen/runtime checks passed**, 16.195s: actual frozen worker invokes external
  Python/helper, observes one passing test, stores/verifies history across restart, handles
  EOF/port collision/missing credential/config and normal worker spawning. No data-file
  packaging hook was needed because helper source is embedded in the imported module.
- [ ] Remaining: artifact readback/hash verifier, broader test frameworks, content-version
  invalidation and current real-model counter acceptance. Managed Ollama manifest access,
  native WebView and NSIS gates remain blocked as previously recorded; none were marked passed.
  This first verifier does not complete P1-02 A/B or the larger platform goal.

Trusted-host limits: approved repository code has Windows user permissions and can attack
the interpreter or reports. This is not OS isolation or same-user attestation. Temporary
metadata is removed on normal completion/denial; a hard process crash may leave a small
helper/count directory in state. It contains no captured console output; no broad deletion
sweep was added. Evidence is point-in-time, not a claim that later edits or test assertions
are correct. See docs/test-verification.md. Logs/snapshot: `.runtime/p1-02-test-verifier/`.

Official references checked: [unittest result/runner interface](https://docs.python.org/3/library/unittest.html),
[Python cache prefix](https://docs.python.org/3/library/sys.html#sys.pycache_prefix), and
[PyInstaller runtime data](https://pyinstaller.org/en/stable/runtime-information.html).
Next increment: P1-02 A's artifact readback/hash evidence, retaining the same approvals.

## Continuous roadmap execution - 2026-10-23: P1-01 tool contracts and profiles

Inspected Tools dispatch/schema generation, all 19 adapter signatures, Worker review setup,
Manager/Store/API, CLI supervision and relevant tests before implementing this increment.
Retained adapter implementations and scope/approval behavior. No new dependency installed.

- [x] Added immutable version-1 `ToolSpec`/`ArgumentSpec` records and profile/registry
  views. Bind/default/type/command-enum validation runs before adapter dispatch; bool is not
  accepted as an integer. Unknown/malformed names and out-of-profile tools fail closed.
  Host-controlled allowlists can only narrow a profile. Untrusted outputs have no provider
  registration or profile-selection path. Existing normalized results and audits remain.
- [x] Compared all 19 final model-facing schemas to the saved pre-increment implementation:
  exact equality. Defaults are recorded/applied internally without adding wire fields.
  Schema comparison evidence: `.runtime/p1-01-tools/schema-baseline.json`.
- [x] Unified preserves all categories; Coding/Browser/Desktop restrict tool categories.
  CLI supervisor forwards `--profile`; launch.ps1 accepts `-Profile`. Authenticated `/tasks`
  and `/slash` carry the selected profile; Manager revalidates before task creation.
  SQLite adds an existing-task default of Unified and records each new task's profile.
  Regeneration reuses the original profile even if a caller requests broader access.
- [x] Frontend tool views include the selector, disabled during execution; history records
  show the actual profile. Rendered testing caught the initially missing Agent-view toolbar,
  which was corrected. API profile is keyword-only at the call site to preserve existing
  positional goal handling; original slash/goal assertions pass unchanged.
- [x] Fourteen new contracts/process/API/migration/CLI cases pass (final targeted run:
  14 passed, 3.884s). Covers all schemas/defaults, immutable views, pre-dispatch rejection,
  empty command configurations, strict scalar types, allowlist narrowing, actual spawned
  workers, real file approval, profile-preserving regeneration and legacy history.
- [x] Final focused rendered/local-browser checks: **four passed**, 7.033s. Actual frontend,
  authenticated backend, socket activity, approval and external unittest execution verify
  Browser-only denial then Coding-only success. Model metadata is a loopback protocol
  fixture with zero inference calls; this is explicitly not real-model acceptance.
  Real Playwright fixture navigation/form/tabs/download/screenshot, denied POST and actual
  browser-to-file dispatcher checks also pass. No physical desktop pass is inferred.
- [x] TypeScript and Vite production build pass (final build 6.23s); seven Node state tests,
  launch-script parse and Ruff pass. Documentation: docs/tool-profiles.md and desktop guide.
  Existing packaged binaries remain their previously recorded P0-05 snapshot; rebuild to
  include this increment. Native/install/NSIS blockers are unchanged.
- [ ] Live model regression is currently externally blocked. First attempt found no service
  and used the wrong coding-test opt-in (that test skipped, not passed). Started the existing
  repository Ollama normally within this managed session: server/GPU discovery worked, but
  opening the Qwen manifest failed with Access is denied. Retried with the correct opt-in:
  six tests ran, one cancellation case passed and five model-dependent cases failed.
  The UI profile check progressed, while the later chat scenario lacked model availability.
  No failed/skipped model case is counted as verified. Model-store ACLs were not changed.
- [x] Stopped only the identified test-started Ollama PID after confirming its executable,
  creation time and empty loaded-model list. No unrelated service/process was stopped.
  To unblock model regression, start `scripts/start-model.ps1` from your normal Windows
  session, verify `/api/tags` includes the configured model, and rerun the opt-ins below.

```powershell
$env:LIVE_STUDIO = '1'
$env:LIVE_STUDIO_FEATURES = '1'
$env:LIVE_STUDIO_UI = '1'
$env:LOCAL_AGENT_MODEL_TEST = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_studio.StudioLiveTests tests.test_studio_features.AttachmentLiveTests tests.test_studio_ui.StudioUITests tests.test_coding_acceptance.LiveCodingTests -v
Remove-Item Env:LIVE_STUDIO,Env:LIVE_STUDIO_FEATURES,Env:LIVE_STUDIO_UI,Env:LOCAL_AGENT_MODEL_TEST -ErrorAction SilentlyContinue
```

Final full regression: **238 unique tests, 211 passed / 27 skipped**, 111.417s; Ruff passed.
One earlier run failed because an existing supervisor test read an empty child PID file
between creation and writing. Its child now publishes the complete PID by rename, keeping
the same process/deadline assertions. Three consecutive focused runs pass (2.045/2.035/2.052s)
and the final full run passes. The final schema-only compatibility adjustment was followed
by targeted contract, UI/browser and full regression checks; no earlier snapshot is
substituted for final evidence.

P1-01 requirement audit: all 19 versioned wrappers, preserved adapters/approvals, explicit
per-run categories, schema/default/error contracts, pre-dispatch malformed/disallowed
rejection, Unified compatibility and host-only registration are independently verified.
The applicable UI/browser/approved-execution checks pass; model-dependent platform
regression is explicitly blocked as recorded above, with no passing inference claim.
P1-01's contract checkbox is complete; native/NSIS and live model gates remain open.
Logs/source baseline: `.runtime/p1-01-tools/`. Next: **P1-02 A**, one independently
persisted configured-test verifier. No MCP, scheduler, isolation or expanded model
capability claim is included. Continuous execution remains active.

## Continuous roadmap execution - 2026-10-22: P0-05 frozen packaging verified, NSIS blocked

Selected the independent second increment while retaining the first increment's native
WebView gate. Read build/template/runtime/coding/browser sources and tests; checked official
PyInstaller multiprocessing/external-program guidance and Tauri installer documentation.

- [x] Built the actual one-file PyInstaller backend with the existing collection options.
  Added an explicit test command selector so runtime/socket contracts run against source
  or a selected frozen executable without duplicating discoverable test implementations.
- [x] Added frozen coding/browser acceptance. The real spawned frozen worker requests
  approval, executes the configured external Python in a disposable workspace, verifies
  one unittest with `sys.frozen == False`, persists its report and preserves it on restart.
  Actual local Qwen3.5 9B drives frozen browser navigation/screenshot, reports the observed
  fixture heading and leaves no owned captures. No model mock in the live browser check.
- [x] Package template now selects installed Edge explicitly; the existing development
  configuration is preserved. No browser/model binaries or external coding Python are
  claimed to be bundled. Source tests verify configured/missing frozen Python behavior.
- [x] New native first-run helper publishes a complete default configuration exclusively
  using an owned temporary file and NTFS hard-link publication. Concurrent creators do
  not overwrite each other; existing settings remain untouched; missing template leaves
  no partial file. Three native tests cover these behaviors. Seven total Rust tests pass.
- [x] Build script supports `-ConfigLoaderRunner` via a temporary overlay for the managed
  Vite loader restriction. New `release-manifest.py` records artifact SHA-256, 47 source/lock
  input hashes and Python build-environment versions. It explicitly distinguishes bundle
  success and installation verification, and is not represented as a complete binary SBOM.
- [x] Ran the complete updated build script: **223 default tests, 197 passed / 26 skipped**,
  109.673s; lint passed; PyInstaller, TypeScript/Vite and optimized Windows release compiled.
  A separate no-bundle release build also passed (15.91s Rust compile, 2.64s Vite).
  PowerShell build-script parsing and script-specific Ruff checks passed.
- [x] Final exact `dist/agent-backend.exe` acceptance: **15 passed, no skips**, 51.283s.
  Includes four runtime/EOF/port/configuration/worker cases, nine authenticated WebSocket
  positive/negative cases, approved external-Python workflow and real-model browser case.
  Earlier isolated-sidecar runs also passed; final evidence refers to the actual build output.
- [x] Independently verified both final artifact hashes using .NET SHA-256 and all 47
  manifest source/lock hashes against current files. The PowerShell Get-FileHash cmdlet
  was unavailable in this managed session; the .NET implementation provided the check.
  A log-printing wrapper encountered console encoding errors after successful subprocess
  completion; retained logs prove the underlying build results, and final log output uses
  safe encoding. No encoding error was counted as an application test failure/pass.
- [ ] NSIS installer blocked: both actual Tauri bundling attempts failed downloading the
  official `nsis-3.13.zip` with Windows socket error 10013. The full build script correctly
  fails and still writes `dist/release-manifest.json` with bundle/installation flags false.
  No installer or clean install/upgrade/native WebView acceptance is claimed. Keep both
  P0-05 first/second checkboxes open; third depends on an installer and a normal desktop.

Final SHA-256:

- `dist/agent-backend.exe`: `3d3d7970b2a4c8fdfd01fa6c1819c1742f25b6de4f6af6b1e26f2ac8eb430162`
- `desktop/src-tauri/target/release/local-agent-studio.exe`:
  `bdf464dd8ff1b5fc3cb56c3b342262f621ccc49ed0bbdc5af172ba92df2ec57e`

Evidence: `.runtime/p0-05-package/` build/frozen logs and `dist/release-manifest.json`.
See docs/desktop.md for the normal-session build and frozen acceptance commands. To resolve
the NSIS blocker, allow the official release download through the normal permitted network
and rerun `scripts/build-desktop.ps1 -ConfigLoaderRunner`; retain existing security controls.
Then verify installer checksum and run the separate standard-user native/install gates.
The next safe independent increment is **P1-01 typed tool registry/capability profiles**,
whose P0-03 dependency is satisfied. Continuous roadmap execution remains active.

## Continuous roadmap execution - 2026-10-22: P0-05 lifecycle, native gate open

Inspected native main.rs, runtime/Manager, model startup, frontend connection/replay,
tests and official Rust Child / Tauri single-instance documentation. Retained the
existing plugin and EOF handling; confirmed discarded stderr, unreaped startup errors
and missing automatic recovery before making changes.

- [x] New `process_output.py`: one owned model process, 8,192-character redacted RAM
  tail, serialized API starts, Job failure compensation, process reaping and reader
  shutdown. Existing Ollama is never adopted/stopped. Authenticated model status and
  the settings panel expose diagnostics/exit code.
- [x] Native `diagnostics.rs`: 4,096-byte input line limit and 16,384-byte output tail
  including separators. Suppresses sensitive/oversized lines, private-key blocks and
  the exact launch credential. New native diagnostic IPC exposes only this RAM tail.
- [x] Backend ownership now cleans up through Drop, including invalid/oversized readiness
  and startup errors: signal shutdown, wait, then kill/reap the owned child if needed.
  Readiness port is validated. No new shell/filesystem capability was introduced.
- [x] Frontend automatic recovery has three attempts per mounted session with 1/2/4-second
  delays and a manual reset. Reuses a live backend and never submits an interrupted task.
  Startup health probes have two-second timeouts, at most ten probes. Rendered tests found
  and fixed React batching an immediate rejection without scheduling the next attempt.
- [x] Default: **219 unique tests, 195 passed / 24 skipped**, 105.661s. Targeted process/
  runtime: eight passed, 6.517s; final diagnostic/API checks: six passed, 0.793s. Rust:
  four passed, including actual child readiness failure/shutdown and real Python missing
  config diagnosis. Node: seven passed. TypeScript, Ruff and Vite production build pass
  (`--configLoader runner`, 2.33s; normal config loading hits the known parent ACL limit).
- [x] Actual Ollama/UI regression plus rendered recovery: **six passed**, 23.638s.
  Recovery test verifies exact count/backoff, manual connection and zero task submissions;
  HTTP/SQLite/WebSocket are real, native discovery is bridged. It reuses verified current
  Vite source if the user's port is occupied. Initial synthetic asset routing failed
  browser network access; serving through the real local frontend resolved that harness issue.
- [x] Rust uses the existing tauri.dev.conf.json overlay: without it the missing packaged
  sidecar correctly blocks compilation. Running Studio locked the regular executable;
  `cargo rustc ... -- -o <workspace>/.runtime/p0-05-lifecycle/studio-validation.exe` built
  an isolated real Windows executable without replacing it.
- [ ] Native acceptance remains open. Actual second-instance attempt exited 101 before
  readiness: WebView2 HRESULT 0x800700AA, shared resource in use. The user's existing
  instance stayed alive; all observed validation descendants subsequently exited. No
  unrelated Studio/Ollama was terminated. A previously observed PID disappeared and was
  revalidated before any action. This managed-session result is not a single-instance or
  native crash/recovery pass. Evidence: `.runtime/p0-05-lifecycle/`.
- [ ] P0-05 first checkbox remains open. Packaging/frozen-worker verification is the next
  independent increment; normal-session native launch/recovery and installed acceptance
  remain gates. No installer or production-readiness claim is made.

References: [Rust Child ownership](https://doc.rust-lang.org/std/process/struct.Child.html),
[Tauri single instance](https://v2.tauri.app/plugin/single-instance/),
[WebView2 test isolation](https://playwright.dev/docs/webview2).
No global WebView debug flags, registry changes or security bypass were applied. Redaction
is best effort; diagnostics are not persistent logs and cannot identify arbitrary secrets.

## Continuous roadmap execution - 2026-10-22: P0-04 image context

Implemented the second increment after inspecting Agent message mutation, browser and
Windows capture adapters, worker preview handling, Manager lifecycle and attachments.

- New `vision.py` retains originals and budgets one transient observation within eight
  images; normalization is shared with attachment parsing. Agent copies incoming history,
  records tool results before visual observations, and reports omissions explicitly.
- New `captures.py` records exclusive PNG identities before writing pixels, with SQLite
  ownership and a process-lifetime lease. Preview/consumption require registered ownership;
  normal close, Studio cancellation and abandoned-run recovery remove only owned files.
  Studio owns the lease before spawning and releases it after stopping owned processes.
- Browser/Desktop share the capture writer through Tools. Approval and application
  ownership boundaries remain unchanged; desktop cleanup does not terminate applications.
- Ten new deterministic checks cover original retention, count/byte/dimension bounds,
  invalid observations, hardlink/replacement refusal, active leases, abrupt subprocess
  exit, joined ownership, unknown-file refusal and Studio cancellation. Existing startup
  fault tests additionally assert no capture ownership directories remain.
- Targeted image/lifecycle/startup checks: 20 passed, 6.594s, no skips. Actual local
  Qwen3.5 9B + Edge browser checks: 2 passed, 13.261s. One instruments real model requests
  and verifies both original and screenshot reach inference; another uses the actual
  spawned Studio worker, verifies preview delivery, correct original color, attachment
  byte preservation and cleanup. No mocked model replies in either acceptance check.
- Initial live attempt failed with connection refused. A repository Ollama launch then
  exited because port 11434 was occupied; the subsequent health probe reported 0.40.7.
  Retried checks passed against that existing service. No unrelated service was stopped.
- Earlier full run: 204 tests, 183 passed / 21 skipped, 100.607s. Final regression: 209 unique tests, 186 passed / 23 skipped, 101.199s; Ruff passed.
  Two new live tests were separately enabled and passed; skips are not counted as passes. Logs: `.runtime/p0-04-images/`; before-source
  archive: `before.zip`. Skips remain unpassed; native physical capture/install validation
  is not inferred. No frontend change or dependency installation was needed.
- Limits: registry/lease checks are not OS isolation against hostile same-user races;
  pixel secrets are not redacted. Unknown/changed files intentionally block cleanup;
  legacy unregistered screenshots are not automatically deleted. Crash recovery does
  not restore or replay agent tasks. Next: P0-05 first increment, native diagnostics,
  owned lifecycle and bounded backend restart.

## Continuous roadmap execution - 2026-10-22: P0-04 first increment verified

After independently verifying/documenting both P0-03 increments, continued to the next
incomplete increment. Inspected raw Ollama streaming, Worker emit, shared `clean`/`redact`,
Manager storage/events and existing fixture/real-model tests. The leak was confirmed:
independent redaction of `password=` and its following value cannot protect their join.

- [x] New `local_agent/redaction.py`: stateful text parser supporting password/passwd,
  api_key/api-key/apikey, token/secret assignments, JSON quoted keys/escaped values,
  Bearer values and private-key blocks. Secret bodies are replaced once and discarded;
  incomplete quoted/private values remain masked at finish/cancellation. Overlong private
  headers fail conservatively. Quoted prose and adjacent/nested headers are regression cases.
- [x] Ordinary text holds at most 16 trailing characters to recognize a split label.
  Total retained parser text never exceeds 128 characters (up to 512 UTF-8 data bytes,
  excluding fixed object overhead). Whitespace and arbitrarily long values do not grow
  state. This bounds redaction buffering, not total response/history/transport memory.
- [x] `safety.redact` shares the complete-text treatment. A cheap no-label precheck avoids
  scanning normal large image encodings character by character. Best-effort scope remains
  explicit; arbitrary encodings/credentials and pixels are not detectable guarantees.
- [x] Worker applies one parser across the entire generation before emitting tokens to
  the parent. Completed report is built from that same safe stream. Ollama token/time
  metrics still count original model generation; no guessed token count or model rewrite.
- [x] Seven parser tests plus two real HTTP/spawned-worker cases: every two-way split and
  one-character chunks, every cancellation prefix, JSON escapes/quotes, mixed-case labels,
  long whitespace/values/private headers and normal streaming. Live Manager state, stored
  messages/events and actual SQLite/WAL bytes contain no seeded canary. Live text equals
  the persisted final report. These protocol fixtures are not described as real inference.
- [x] Preserve existing streaming/metrics/no-token-storage assertions. Replace the old
  incidental two-frame assertion with nonempty live chunks whose exact join is `hello
  world`; a safety buffer deliberately changes frame boundaries. Fixture final-gate
  disconnect handles expected cancellation without a server-thread traceback.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Default regression | 197 unique tests: 176 passed / 21 skipped, 98.519s | `.runtime/p0-04-streaming/regression.log` |
| Final privacy/worker/policy | 23 tests: 22 passed / 1 explicit symlink skip, 3.820s | `.runtime/p0-04-streaming/targeted-final.log` |
| Actual Ollama/UI | 5 passed, no skips, 31.729s | `.runtime/p0-04-streaming/live.log` |
| Ruff | Passed | `python -m ruff check local_agent tests scripts/create-icon.py` |

The 188-to-197 count increase is exactly nine new default cases. Default skips are not
passes; final targeted skip is the existing unavailable Windows symlink privilege, not
privacy coverage. Real native junction defense already passed separately in P0-03.
Final targeted checks followed small quoted-prose/non-private-header grammar corrections;
the full regression and live run preceded those corrections. Final tests exercise every
changed grammar branch plus real worker/state/storage behavior. No frontend code changed,
so the existing production UI assets were used for the actual inference checks.

Initial protocol test failed solely because safe buffering coalesces short model chunks;
its semantic content/metrics/storage assertions are preserved and now pass. A deliberate
cancel initially made the fixture HTTP server print a connection-reset traceback; the
fixture now recognizes that expected terminal-send disconnect. Ruff alias warnings were
corrected. No failed capability was hidden behind a skip.

No external blocker remains for this increment. Restart the Python backend to load the
new worker/cleaner. Unknown secret formats, arbitrary unlabeled/encoded strings, raw
attachments/project files and screenshot pixels remain outside textual detection; this
is not encryption. Bounded lookbehind can delay the final 16 ordinary characters until
more output or stream completion. Truncated private/quoted forms may over-redact, rather
than publish a possible value. Image-context retention/owned screenshot cleanup remains
P0-04's second increment, not completed by this text change.

Next actionable increment: P0-04 second increment, retaining original user images when
adding transient screenshots and safely handling owned screenshot lifecycle. Continuous
roadmap execution remains active; no user reauthorization is required for ordinary scoped
implementation. AGENTS.md/configuration/lockfiles were preserved. Source-before archive and
logs are under `.runtime/p0-04-streaming/`.

---

## Continuous roadmap execution - 2026-10-22: P0-03 second increment verified

Completed the first increment and recorded its evidence before proceeding. Reused the
Policy/Coding/Browser paths; inspected actual Git execution/configuration and download
publication. No extra framework or dependency was installed.

- [x] New `file_ops.py`: same-directory owned staging, fsync before text publication,
  checked preimage/parent identities, exclusive `os.link` for new files/downloads and
  native Windows `ReplaceFileW` for reviewed overwrites. Staging cleanup occurs on
  success/failure. No overwrite fallback is used when exclusive publication fails.
- [x] Preserve Windows DACL rights, ACE flags and protection. Replacement checks access
  to retain security before changing bytes and restores the exact DACL after native
  replacement. Protected and unprotected actual-file cases pass. Permission failure is
  an error, never a request to weaken ACLs or acquire administrator access.
- [x] Browser saves the real Playwright download to owned staging, then rechecks policy,
  parent and destination before exclusive publication. Pre-existing, approval-time and
  late destination winners are preserved; downloaded files remain untrusted.
- [x] Policy write/Git-metadata checks reject symlink, junction and other reparse ancestors;
  retain hardlink checks. An actual Windows junction and a hardlink introduced during
  review are refused. One staging-reparse case is explicit fault injection, not claimed
  as a real symlink test (Windows symlink privilege is still unavailable).
- [x] Git guards inspect bounded non-including config without returning its values to the
  model. Reject clean/smudge/process/textconv/external-diff/signing/credential/SSH helper
  configuration and includes. Recheck config after approval; disable hooks/fsmonitor,
  signing, signature display and automatic maintenance for supported actions. Read Git
  operations also validate repository/worktree scope. No user Git configuration is changed.
- [x] Twelve new default `test_publication.py` cases plus three real opt-in
  `test_browser_publication.py` cases. Existing reviewed-write race test now injects at
  atomic publication rather than the superseded in-place-open implementation.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Final default regression | 188 tests: 167 passed / 21 skipped, 100.179s | `.runtime/p0-03-publication/regression-final.log` |
| Final publication/review/coding | 29 passed, no skips, 13.020s | `.runtime/p0-03-publication/targeted-final.log` |
| Actual local browser | 6 passed, no skips, 8.366s | `.runtime/p0-03-publication/browser.log`; three new download cases plus existing navigation/form/tabs/download, denied POST and browser-to-file checks, Edge headless |
| Actual Ollama/UI/coding | 6 passed, no skips, 61.616s | `.runtime/p0-03-publication/live.log`; five Studio/UI scenarios plus real autonomous counter acceptance with eight project tests, independent rerun and six private behavior tests |
| Ruff | Passed | `python -m ruff check local_agent tests scripts/create-icon.py` |

The 173-to-188 increase is twelve default checks plus three opt-in browser checks; default
skips increase from 18 to 21. The opt-in browser checks passed separately, not in default
regression. The final suite includes the final read-scope guard and enhanced DACL tests;
existing live checks preceded the last read-scope guard and are backed by final targeted
and default scope tests. No frontend code/assets changed; no unrelated frontend rebuild.

Diagnosed Windows behavior rather than masking a test: ReplaceFileW retained granted
rights but relabeled ACEs as inherited. Comparing the actual DACL/protection confirmed
this was more than descriptor-layout variation. Exact security-descriptor restoration
now passes both protected and unprotected tests. Initial failed test runs remain in tool
history; final pass evidence is above. An earlier 187-test run passed before the external
worktree regression was added; it does not replace the final 188-test evidence.

Boundaries: this is trusted host execution, not OS isolation. Same-user adversarial races
between the final version check and native path/Git operations remain outside the tested
cooperative-review contract. A failed OS call after publication may have completed an
effect; no rollback/success guarantee is invented. Owned temp files can remain after a
hard process crash; there is no new execution journal. File-system hardlink support and
ability to preserve Windows DACLs are required; failure never falls back to overwriting.
Git includes/LFS-style filters/signing need a separately reviewed manual workflow; do not
remove security checks or silently modify repository config to make them pass.

Both P0-03 checkboxes now meet their bounded acceptance criteria. R4's review/publication
issues are addressed; R7's OS-isolation limitation remains for P1-07. Native UI/installer
acceptance remains separate. Next: P0-04 first increment, bounded streaming redaction.

References reviewed: [ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew),
[Git attributes](https://git-scm.com/docs/gitattributes), [Git config](https://git-scm.com/docs/git-config),
[Python file operations](https://docs.python.org/3.12/library/os.html). Before-state archive
and all logs are under `.runtime/p0-03-publication/`; no user project/config or root Git
commit was overwritten/created.

---

## Continuous roadmap execution - 2026-10-22: P0-03 first increment verified

Continuous execution was explicitly requested. Read the current AGENTS.md (including its
new roadmap workflow), ROADMAP, architecture/gap findings and implementation history;
inspected Coding, Policy, Tools, Studio approval/worker paths and relevant tests. Existing
one-use/expiring approvals were preserved. The missing preimage/index checks were confirmed
in source before changes. This entry records the first increment independently before
proceeding to P0-03's second increment.

- [x] New `local_agent/review.py`: bounded SHA-256 plus regular-file identity, size, mtime
  and link count. Recreated identical-byte files conflict; resource changes produce a
  `Denied` review-conflict response requiring a new review, not automatic reapproval.
- [x] `coding.py`: verify file versions around diff generation, after approval and before
  writing; open existing files without truncation and check the opened identity. New
  files retain exclusive creation. Studio creation reviews now live inside Coding via
  trusted `review_create`; the model's path/text schema has not widened.
- [x] Capture the actual Git index/HEAD identity and HEAD tree before staged diff review;
  revalidate before approval and before commit. Bind staging to file and index versions.
  Metadata outside the approved workspace is refused; large/incomplete reviews fail
  closed. No root repository commit/stage or global Git configuration was performed.
- [x] `studio/worker.py`: reuse Coding's reviewed create path, eliminating the previous
  gap between separate UI creation approval and the actual file operation.
- [x] Ten new `tests/test_review.py` cases: changed/deleted/recreated content, identical
  index replacement, concurrent HEAD/tree update, stage input changes, no-op/schema
  preservation, denied operations, last-moment path replacement and fresh retry.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Targeted review/coding/worker | 20 passed, 7.883s | `python -m unittest tests.test_review tests.test_coding tests.test_studio.StudioProcessTests -v` |
| Full default | 173 unique tests: 155 passed / 18 skipped, 85.624s | `.runtime/p0-03-review/regression.log` |
| Actual Ollama and UI | 5 passed, no skips, 31.478s | `.runtime/p0-03-review/live.log`; contextual stream, real read tool, cancellation, both attachment/slash UI scenarios |
| Ruff | Passed after test closure binding correction | `python -m ruff check local_agent tests scripts/create-icon.py` |

The ten added cases explain the default count increase from 163 to 173; default skips are
not passes. No frontend code changed, so an unrelated frontend rebuild was unnecessary.
Existing live UI used the already validated production assets with the real changed worker.
No new dependencies or machine configuration were needed. Source-before snapshot:
`.runtime/p0-03-review/before.zip`.

A real Windows test initially exposed differing path/handle ctime values following Git's
atomic file rename. ctime is not compared across those APIs; identity/size/mtime and the
content digest provide the version check. Original stage/commit regression then passed.
Ruff requested binding the subtest closure's loop values; that was corrected and lint passes.

The first P0-03 checkbox is complete; the overall item remains open until the second
increment. Atomic reviewed replacement/download publication and Git filter/signing/helper
restrictions are not claimed yet. Small host path/process races remain; versions are not
an OS sandbox or protection against an adversarial process with the same user privileges.
Command/test execution still requires approval. Approval expiration/replay tests stay in
regression. Native desktop/installer acceptance was not rerun.

Next, without a permission pause: P0-03 second increment. Official references reviewed:
[Git rev-parse](https://git-scm.com/docs/git-rev-parse) and
[Python 3.12 stat/file APIs](https://docs.python.org/3.12/library/os.html).

---

## Latest progress ? 2026-10-22 (P0-02 third increment completed)

Selected the next actionable increment after rereading AGENTS.md, ROADMAP.md, this history,
architecture R1?R3 and feature contract F01, then inspecting the actual Store/Manager/API,
React event subscription and existing tests. Startup/lifecycle compensation already worked.
The remaining defect was source-confirmed: a single 1,000-row replay followed by the latest
RAM cursor could drop durable history; the UI appended replay without deduplication.

### Completed requirement checklist and files

- [x] `store.py`: additive persisted database identity; allocated high-water cursor survives
  deletion; bounded `event_page(after, through)` reads at most 200 rows with a 256 KiB target.
  Existing legacy reads, messages, task transactions and recovery remain intact. Writes
  beyond a captured boundary arrive in subsequent catch-up, including committed rows absent
  from the RAM ring. No action is re-executed by event recovery.
- [x] New `event_stream.py` and API integration: authenticated snapshot ? paginated replay ?
  ready ? live delivery. One numbered delivery awaits its exact integer acknowledgment;
  clients cannot use an acknowledgment to jump to an arbitrary event cursor. Send/ACK
  budgets are 5s/10s; slow clients close with 1013 and can reconnect from their accepted
  cursor. Invalid acknowledgments close 1008, oversized frames 1009, storage failures 1011.
  Origin/token/64-bit input validation and local-only privileged API remain enforced.
- [x] `manager.py`: serialize durable commit/publication with snapshot capture; assign a
  fresh backend epoch and bound the shared ring to 4,000 records / 16 MiB. Conversation
  deletion updates byte accounting. A missing RAM range explicitly triggers a `ram_gap`
  snapshot, authoritative streams/pending approvals and durable catch-up. Live-only
  approval/preview bodies survive normal delivery; stale previews clear on reconciliation.
- [x] New `desktop/src/eventHistory.ts`, `App.tsx` and `desktop/tests/eventHistory.test.mjs`:
  validate complete packets before cursor advancement; deduplicate durable IDs and
  epoch-scoped transient sequences across reconnect/restart. Retain at most 10,000 activity
  records / 16 MiB, display the latest 40, preserve the accepted cursor after trimming.
  Token bodies stay outside history; preview/approval history uses placeholders. Historical
  replay cannot open an approval or revive a screenshot. Ready checkpoints refresh messages,
  goals and tasks once per catch-up, including durable-only commits; live batches refresh
  once when needed. Accessible retained-count text enables actual UI-state acceptance.
- [x] Preserve transient privacy: tokens are never inserted into SQLite; approval/preview
  bodies are not persisted. Pending approvals are supplied only by current authoritative
  manager state. No new approval authority, tool capability or model configuration.
- [x] Extract the existing socket fixture into plain `tests/studio_socket_support.py`,
  preserving all nine authentication tests. Extend discovery guards; no inherited duplicate
  tests. Add 14 default-enabled checks in `test_studio_replay.py` and
  `test_studio_event_delivery.py`, plus one opt-in `test_studio_replay_ui.py` scenario.
- [x] Update ROADMAP.md, README.md, docs/desktop.md and the architecture/gap implementation
  annotations. No framework/dependency installation was needed: existing Python packages,
  Edge/Playwright and Node v24.22.1 suffice. Add `npm test` using Node's built-in runner and
  TypeScript type stripping; lockfiles and the P0-01 immutable source manifest are unchanged.

### Verification and evidence

| Check | Observed result | Evidence / scope |
| --- | --- | --- |
| Full default regression | **163 unique tests: 145 passed / 18 skipped**, 79.192s | `.runtime/p0-02-replay/regression-final.log`; existing lifecycle/startup/policy/discovery/security regressions included. |
| Final replay/delivery/rendered UI | **15 passed, no skips**, 25.531s | `.runtime/p0-02-replay/delivery-final.log`; real SQLite, loopback backends, ASGI and Edge frontend. |
| Existing live Ollama/UI | **5 passed, no skips**, 32.478s | `.runtime/p0-02-replay/live-ui-initial.log`; actual contextual generation, read tool, cancellation, attachments/slash/approval and real storage-lock recovery. |
| Frontend state tests | **6 passed, zero skipped**, 117.3372ms final run | `cd desktop; npm test`; 5,001-event deduplication/restart, identity reset, transient privacy, invalid gaps, RAM reconciliation and retention bounds. |
| Python lint | **Passed** | `python -m ruff check local_agent tests scripts/create-icon.py` after final code changes. |
| TypeScript / production assets | **Passed** | `desktop/node_modules/.bin/tsc.cmd --noEmit`; `vite.cmd build --configLoader runner` built in 2.41s. No Rust/installer or native IPC pass inferred. |

The final 15-case delivery run followed the full regression and covers the last small
protocol correction: catch-up of durable-only commits also emits a ready checkpoint, so
UI messages/task status refresh without replaying historical approval effects. The five
live Ollama/UI checks ran before that correction; ordinary live delivery was unchanged.
Both the final delivery run and the Node tests check the changed recovery behavior.

The 148 ? 163 discovery increase is exactly 14 default checks plus one opt-in rendered
replay test. The extra default skip is that new opt-in UI test; all 18 skips are unpassed
in default regression. It was separately enabled and passed in the 15-case run. Existing
five live scenarios also passed separately; these are not extra distinct discovered tests.

Acceptance exercises all 5,001 ordered IDs, disconnect before ACK with overlapping replay,
backend restart with unchanged store identity/new epoch, concurrent writes after the
captured boundary, deleted-row holes, database replacement, malformed ACKs and a real
10-second unacknowledging peer that cannot stall `/health`. RAM overflow reconciles current
stream/approval state and catches up all durable observations. Byte-limit, oversize and
blocked-transport tests verify bounded failure. The rendered UI retains exactly 5,001
entries after reconnect/restart and exactly 5,002 after one new event; no REST or event
responses are intercepted. Only native connection discovery is bridged. Screenshot:
`.runtime/p0-02-replay/ui-restart.png`.

Initial diagnosis: the first UI acceptance body passed, but a redundant browser cleanup
ran after Playwright had closed its event loop. Removed the redundant cleanup; the scenario
and final combined delivery run pass. A Ruff nested-context warning was corrected. Early
PowerShell native-stderr pipeline reporting produced a nonzero shell wrapper despite a
passing Python run; final evidence uses a Python subprocess wrapper preserving the actual
exit status. An initial regression (162 tests, 80.425s) passed before the last edge-case
check was added; final counts above supersede it. No application failure is hidden as a skip.

### Limits, blockers and next increment

No blocker remains for P0-02's third increment. All three P0-02 checkboxes now satisfy their
bounded acceptance criteria. Display retention is finite; full paged activity browsing and
configured retention remain P1-06. Individual frames have a documented 16 MiB ceiling and
are explicitly rejected, never silently skipped. Persistent database/OS failure still
cannot be certified as a committed result. Existing best-effort redaction, chunk-boundary
privacy concerns (P0-04), host execution and native/install limitations remain unchanged.

Restart the full Studio application (`.\desktop-dev.ps1`) after updating: the event wire
protocol now requires delivery acknowledgments on both sides. No unrelated Ollama/Python
process was terminated. Native Tauri/WebView2, interactive desktop and installer acceptance
were not rerun; passing a browser connection bridge does not establish those capabilities.

Next actionable increment: **P0-03, first increment** ? fingerprint reviewed file preimages
and Git index/tree, revalidate after approval/immediately before mutation, fail with a fresh
review on conflict. Its dependencies are present; it is deliberately not implemented here.

Implementation uses the existing stack and documented primitives:
[Python asyncio wait_for](https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for)
for bounded awaited I/O and [Node TypeScript execution](https://nodejs.org/api/typescript.html)
for dependency-free reducer tests. Before/after source snapshots, review diff and validation
metadata are under `.runtime/p0-02-replay/`; the original Git repository still has no commits.

---

## Latest progress — 2026-10-22 (P0-02 second increment completed)

Selected P0-02's next incomplete increment after reviewing AGENTS.md, ROADMAP.md, the
implementation history, architecture R1–R3, feature contract F01 and actual Manager/Store/
worker/API/UI source and tests. Startup compensation was already complete. Terminal writes
were separate, monitor exceptions were not reconciled, and readiness had no heartbeat or
deadline contract. Durable replay is the following increment and was deliberately left open.

### Changes and requirement checklist

- [x] `store.py`: add idempotent `complete()` with `BEGIN IMMEDIATE`. Task status/result,
  assistant message/metrics, result event and planned goal checklist commit together.
  Competing terminal writers have one winner; failed SQL rolls everything back. Restart
  recovery now atomically records interrupted outcomes/messages/events without running code.
- [x] `manager.py`: serialize cancellation/result selection; stop/reap the owned worker,
  close its Windows Job Object/descendants, pipe and Process handle, then persist/publish
  the selected outcome. Catch poll/receive/event/approval/monitor failures. Cleanup errors
  retain ownership for retry; failed terminal persistence retains only the outcome, blocks
  new work and retries storage, never model/tool actions or approval delivery.
- [x] Bound SQLite busy waits to 0.2 seconds so storage contention cannot hold cancellation
  behind the old ten-second wait. Cancellation stops the worker even while the database
  is write-locked. Degraded `/health` and task runtime state expose pending persistence;
  SQLite request errors return authenticated HTTP 503 instead of an unhandled server error.
- [x] `worker.py`: serialize all pipe writers, send transient independent heartbeats and
  explicit model phases; existing tool-start/readiness events establish the other phases.
  Model/tool/execution and total-task budgets are enforced independently of token traffic.
  Worker tool cleanup precedes its terminal result. No heartbeat is stored or displayed.
- [x] Persist `waiting` while approvals are pending. Nested approvals retain that state;
  resolving the last request restores remaining active budgets. Expired approvals block
  execution, late clicks cannot discard the expiry boundary, and waits remain cancellable.
  Approval bodies remain transient. This is not pause/checkpoint/resume support.
- [x] Separate reusable emergency stop from permanent backend shutdown in API/runtime.
  An uncommitted outcome during unavailable storage is marked interrupted at the next
  working startup. Stop never terminates an unrelated model/Python process or replays work.
- [x] Frontend/API task snapshots distinguish pending storage/cleanup from active work;
  show storage failure/recovery notices and `Submitting` until submission finishes.
  Disable conversation deletion for both running and approval-waiting tasks.
- [x] Add `test_studio_completion.py`, `test_studio_supervision.py` and the plain spawnable
  `lifecycle_worker.py` fixture: **30 new tests**. These use actual SQLite rollback/write
  locks, worker processes/pipes/Job handles and local protocol servers, with explicit fault
  injection. They validate no orphan/duplicate terminal row, redaction, restart/no replay,
  graceful resource retry and cancellation within five seconds in controlled fixtures.
- [x] Extend real slash UI acceptance with disabled deletion during approval and cancellation
  under an actual database write lock: display `Waiting for storage`, remove approval,
  release the lock, observe one cancelled result and return to `Ready`. UI diagnostics
  save at most 16,000 redacted stderr characters for the test-owned backend.

### Final verification and diagnosed failures

| Check | Final observed result | Evidence |
| --- | --- | --- |
| Full default regression | **148 unique tests, 131 passed / 17 skipped**, 60.316s | `.runtime/p0-02-terminal/regression-final.log`; includes all 30 new tests and discovery/startup/socket/policy regressions. |
| Actual Studio/Ollama plus browser UI | **5 passed, no skips**, 30.616s | `.runtime/p0-02-terminal/live-ui-final.log`; three contextual-stream/read-tool/cancel tests and both chat/attachment/slash UI scenarios against Ollama 0.40.7. |
| Python lint | **Passed** | `python -m ruff check local_agent tests scripts/create-icon.py`. |
| TypeScript and production assets | **Passed** | `desktop/node_modules/.bin/tsc.cmd --noEmit`, then `vite.cmd build --configLoader runner`; final build 2.51s. No native IPC/install acceptance inferred. |

A final approval-error wording check also passed (1 test, 0.736s), followed by Ruff:
errors after approval handling explicitly warn that completed actions were not undone,
since a delivery can succeed before a later persistence failure. This wording change does
not claim that an approved action was necessarily prevented.

The 118 → 148 increase is exactly 30 new default-enabled cases; the 17 default opt-in/
symlink skips remain unpassed in that run. Five live tests were separately enabled and
passed, not counted as five extra distinct tests. Existing deterministic helpers are not
claimed as real inference; the separate live suite uses the actual local model service.

Initial fault-test failures were diagnosed: live event objects intentionally omit SQLite's
`created` field, and safe process-kill retries can occur more than once; assertions now
check durable content and actual cleanup rather than incidental call counts. Live testing
then exposed queued heartbeat handling and premature frontend `Ready` during submission.
The heartbeat check now drains queued liveness before declaring a heartbeat lost while
retaining absolute phase/task limits; a deterministic delayed-parent test covers it. The
initial look-ahead fix exposed Windows error 109 when the writer closes after its final
frame. `_queued()` now treats look-ahead EOF as no further frames, preserving the already
received result; a specific regression test verifies this. The intermediate failed default
and UI logs remain in `.runtime/p0-02-terminal/`; only the final runs above establish success.

### Defaults, limitations and remaining work

Optional `[execution]` configuration is documented in `docs/desktop.md`: readiness 15s,
heartbeat loss 10s, model phase model HTTP timeout + 15s (135s with current config), tool
120s, other execution 30s, active task 3,600s and approval wait 300s maximum. Valid human
approval waits suspend phase/task budgets; worker liveness is still required. Limits must
be finite positive seconds. No existing configuration or dependency/lockfile was changed.

Permanently unavailable/corrupt storage cannot durably record a result. The owned worker is
stopped, health is degraded and new tasks stay blocked until recovery. Shutdown never
claims that a missing commit succeeded; restart marks unfinished work interrupted when
SQLite becomes available. Persistent OS refusal to close owned resources similarly retains
ownership/degraded health rather than silently declaring success. Same-user approved code
is still not OS-isolated. These mechanisms do not provide safe checkpoint resume.

Physical/public acceptance retains the earlier user-run evidence; those checks were not
repeated in this managed session. Native Windows lifecycle, frozen workers, Rust/release
linking and NSIS installation were not revalidated or claimed. Restart the Studio backend
(and reload its frontend) to use the updated worker protocol. The immutable P0-01 baseline
is unchanged; this increment's source snapshot, review diff, hashes and validation metadata
are under `.runtime/p0-02-terminal/`.

**Next actionable increment:** P0-02 third increment — paginated durable event replay to a
captured high-water mark, UI deduplication, bounded slow clients and explicit RAM-gap recovery.
The 5,001-event/restart acceptance is still unchecked; P0-02 as a whole remains incomplete.

## Prior progress — 2026-10-22 (P0-01 real coding acceptance completed)

Selected the only remaining P0-01 gate after reviewing AGENTS.md, ROADMAP.md, architecture,
gap contracts and actual Agent/Tools/Policy/Coding/model/test source. The existing deterministic
coding cycle and model protocol checks did not establish autonomous debugging. No change to
production orchestration or the security boundary was necessary.

### Implementation and acceptance checklist

- [x] Add the plain `tests/coding_acceptance.py` fixture: disposable Git repository with a
  deliberately broken counter and three trusted seed tests staged for a reviewable diff.
  Seed tests must remain byte-identical. No real project is edited, staged or committed.
- [x] Reuse actual Agent, local Ollama and Tools. The test exposes only file, command and
  Git tools; its automatic approvals are confined to the exact unittest argv/workspace,
  counter/extra-test overwrites and read-only Git status/diff. Other profiles, staging and
  seed-test overwrites are denied. This is a test-only approval policy, not an app bypass.
- [x] Require observed file inspection, failing assertion before the edit, model-generated
  counter correction and regression tests, a nonzero passing test run and final diff review.
  Re-execute the project tests independently, then run six trusted counter behavior checks
  from outside the model's file-tool scope in a separate Python interpreter.
- [x] Add six deterministic tests of the acceptance verifier: real failure/fix/pass cycle,
  false-success prose, zero/skipped/empty generated tests, changed seed tests, missing
  inspection/failure/rerun/generated-test/diff evidence and unapproved operations. These
  test the verifier; only the separate live test establishes model-generated debugging.
- [x] Run `tests.test_coding_acceptance.LiveCodingTests` against the existing normal-session
  Ollama service, with the configured model rather than a hardcoded model or stub.
- [x] Run relevant verifier tests, default regression and Ruff. Complete the P0-01 acceptance
  parent and coding checkboxes only after all gates have evidence; keep other roadmap items open.

### Fresh verification

| Check | Actual result | Evidence |
| --- | --- | --- |
| Verifier positive/negative suite | **6 passed**, 2.473s | Also included without skips in the full regression. |
| Real local-model coding acceptance | **1 passed, no skips**, 20.049s | `.runtime/p0-01-coding/live.log`; Qwen3.5 9B through Ollama 0.40.7. |
| Agent's execution | Initial tests **exit 1**, then **8 tests passed**, final diff reviewed | Five extra tests were model-generated; decrement changed from `+= 1` to `-= 1`. |
| Independent verification | Project **8 passed**; separate oracle **6 passed** | Logged with the observed tool evidence and reviewed diff, after verification succeeds. |
| Default regression | **118 unique tests: 101 passed / 17 skipped**, 33.146s | `.runtime/p0-01-coding/regression.log`; new live coding test explicitly skipped by default. |
| Ruff | **Passed** | `python -m ruff check local_agent tests scripts/create-icon.py`. |

The live run used eight inference calls (1,341 generated tokens, weighted generation rate
75.04 tokens/s). This is one task's measured run, not a broad performance/reliability claim.
The source had one earlier successful live run before expanding verifier coverage/logging;
the table reports the final run. The six helper tests plus one live test explain 111 → 118
unique tests. The extra default skip is intentional; none of the 17 skips is counted as passed.

Ollama initially refused connections (10061). A temporary assistant-owned startup could
start the server but `/api/tags` was empty and its log reported access denied to the existing
model manifest. That owned process was stopped; no permissions, weights or unrelated process
were changed. After requesting a normal-session server, the configured endpoint became
reachable and listed Qwen3.5 9B; that existing service supplied the successful live runs and
was left running. `.runtime/p0-01-coding/ollama-preflight.log` records the earlier failed
model-store access, which is distinct from the successful normal-service inference.

Run the new gate without public-network or physical-desktop prerequisites:

```powershell
$env:LOCAL_AGENT_MODEL_TEST = '1'
try {
    .\.venv\Scripts\python.exe -m unittest tests.test_coding_acceptance -v
} finally {
    Remove-Item Env:LOCAL_AGENT_MODEL_TEST -ErrorAction SilentlyContinue
}
```

The existing `./scripts/validate.ps1 -Model` also includes this test. Model opt-in therefore
executes generated Python in a disposable repository with Windows user permissions; it is
not OS isolation. Inference failures or a missing configured model fail enabled acceptance,
rather than silently skip it. No packages, locks, app code, native assets or build pipeline
changed; no installer/native lifecycle/other-model pass is claimed. Public and Notepad gates
retain the user-reported evidence below; they were not repeated from the restricted runner.
The immutable first-increment source manifest is unchanged; current logs/hashes are under
`.runtime/p0-01-coding/`.

**Next actionable increment:** P0-02 second increment: atomic terminal task/message/event
updates, monitor/pipe/storage/cancellation failure handling, readiness/heartbeat and
phase-aware deadlines with explicit approval-wait state. It has not been implemented here.

## Prior progress — 2026-10-22 (P0-01 user-reported Notepad acceptance)

Following the requested normal-session command `./scripts/validate.ps1 -Desktop`, the user
supplied the end of the supervisor cancellation test and the suite summary:

```text
Emergency stop: agent process tree terminated; completed actions cannot be undone.
ok

----------------------------------------------------------------------
Ran 111 tests in 48.994s

OK (skipped=15)
```

- [x] Record **96 passed / 15 skipped**, with no failures or errors, as user-reported
  normal-session evidence. The full per-test log was not supplied. Rechecked the script's
  flags and `LiveDesktopTests.test_notepad_write_save_readback`: `-Desktop` enables this
  single physical desktop test; the one fewer skip than default discovery is consistent.
- [x] Accept the scoped Notepad workflow: launch the approved app, enter sample text,
  save to the temporary workspace and assert file existence and text readback. Mark only
  this desktop gate complete in ROADMAP.md and update README.
- [x] Inspect `tests/test_supervisor.py`: its intentionally blocked local model protocol
  fixture triggers a stop, expects status 130 and requires completion within five seconds.
  The emergency-stop line followed by `ok` is expected test output, not a failed user task
  or evidence that real Ollama inference ran.
- [ ] Real model-driven coding bug-fix acceptance in a disposable project remains open.

No application/test/configuration/dependency changes or fresh assistant-run tests were
needed for this documentation-only update. Skips are not passes. Managed desktop error 5
remains separate from the successful normal-session Notepad run. Wider UIA/menu/screenshot
coverage, native Studio lifecycle and installer acceptance are not established by this test.
P0-01 remains incomplete only on its real model-driven coding acceptance gate.

**Next increment:** implement and run that disposable-project coding acceptance with real
local inference, including an intentionally failing test, model-generated correction and
passing verification. Existing deterministic coding tests and prior model tool-call checks
do not substitute for that missing combined acceptance test.

## Prior progress — 2026-10-22 (P0-01 user-reported browser acceptance)

Following the requested normal-session command
`./scripts/validate.ps1 -Browser -BrowserChannel msedge`, the user supplied:

```text
----------------------------------------------------------------------
Ran 111 tests in 36.246s

OK (skipped=12)
```

- [x] Record this as **99 passed / 12 skipped**, with no failures or errors, attributed to
  the user's run rather than an assistant-executed rerun. The complete per-test log was
  not supplied. The requested script enables all four LiveBrowserTests; the four fewer
  skips compared with default discovery agree with that configuration.
- [x] Accept the repaired public browser check in the user's normal Windows session:
  TodoMVC extraction, client app-route navigation, two tabs and an unsubmitted draft.
  The same browser group covers local full-page navigation, downloads/screenshots,
  file dispatch and a denied external POST. Source assertions were rechecked against
  the requested validation flags before updating the checklist.
- [x] Mark only the public browser acceptance gate complete in ROADMAP.md; refresh README.
  No application code, configuration, dependencies or tests changed in this update.
- [ ] Physical Notepad launch/type/save/readback: not established by a browser-only run.
- [ ] Real model-driven coding bug-fix acceptance: not established by this run.

The latest managed-session public run remains network-denied; this does not contradict
the successful normal-session result. No DNS/security settings were changed. The 12
skipped tests remain unverified, and P0-01 as a whole remains incomplete. No fresh test
execution was needed for this documentation-only evidence update; prior default/lint
results remain those recorded below.

**Next acceptance action:** run `./scripts/validate.ps1 -Desktop` from an unlocked normal
Windows session without concurrent input; it launches and types into a test Notepad window.
Preserve unrelated work and close only the test window after validation. Real coding
acceptance remains the next independent engineering gate when local inference is available.

## Prior progress — 2026-10-22 (P0-01 public browser test repair)

User-provided normal-session output reached example.com and extracted its body, then failed
the old `Example Domain` assertion. That is evidence of successful public access in that
session, not another DNS/permission failure. The excerpt does not establish the final suite
status or a desktop pass. The current page also explicitly discourages use for testing.

- [x] Inspect AGENTS.md, the relevant roadmap/history, Browser adapter, live tests and
  validation script. Confirm current public content and Playwright's retrying assertions
  against official sources: https://example.com/, https://demo.playwright.dev/todomvc/ and
  https://playwright.dev/python/docs/test-assertions.
- [x] Update only `tests/test_live.py` behavior: use Playwright's TodoMVC testing demo for
  public extraction, client app-route navigation and two tabs; fill an unsubmitted draft
  and assert that no todo was created. Wait for rendered heading/value rather than racing
  initial JavaScript rendering. Reject network mutations and record attempted non-read
  requests as test failures. No Enter, submission, model call or permission expansion.
- [x] Preserve existing local full-page navigation, download, file-dispatch and denied-POST
  coverage. Application code, dependencies, configuration and AGENTS.md are unchanged.
- [x] Run all four browser tests with Edge: **3 passed, 1 error**, 10.900s. The updated public
  check still reports `ERR_NETWORK_ACCESS_DENIED` at the demo in this managed environment;
  none of its later assertions is claimed to have passed here.
- [x] Run default regression: **111 unique tests, 95 passed / 16 skipped**, 30.810s. Skipped
  public/model/physical-desktop/UI checks are not passes. Ruff passed.
- [ ] Obtain a normal-session pass of the updated public test; P0-01 stays incomplete.

Evidence: `.runtime/public-browser-page-fix/{browser,regression,lint}.log`. Browser command:
`python -m unittest tests.test_live.LiveBrowserTests -v` with `LOCAL_AGENT_BROWSER_TEST=1`
and `LOCAL_AGENT_BROWSER_CHANNEL=msedge`. Default regression and Ruff commands match the
prior section. No desktop/model/build checks were rerun for this test-only fix.

Rerun just the changed public check from normal PowerShell in the repository root:

```powershell
$env:LOCAL_AGENT_BROWSER_TEST = '1'
$env:LOCAL_AGENT_BROWSER_CHANNEL = 'msedge'
try {
    .\.venv\Scripts\python.exe -m unittest tests.test_live.LiveBrowserTests.test_public_websites -v
} finally {
    Remove-Item Env:LOCAL_AGENT_BROWSER_TEST, Env:LOCAL_AGENT_BROWSER_CHANNEL -ErrorAction SilentlyContinue
}
```

The full browser validation command remains `./scripts/validate.ps1 -Browser -BrowserChannel msedge`.
Physical Notepad and real model-driven coding acceptance remain open. This repair does not
complete unrelated roadmap work; next is the normal-session public rerun, then the independent
coding acceptance or P0-02 second increment as prerequisites permit.

## Prior progress — 2026-10-22 (P0-01 WebSocket acceptance gate)

Resumed P0-01 following the user's DNS repair. Fresh `getaddrinfo` checks now resolve
example.com and demo.playwright.dev. The actual existing public browser test was run and
failed with **ERR_NETWORK_ACCESS_DENIED** at example.com, replacing ERR_NAME_NOT_RESOLVED.
The read-only desktop cursor probe still returns false/error 5. No network controls or
Windows permissions were changed. Requested normal-session desktop test output while
continuing independent work; no such evidence was available at completion of this gate.

The bundled P0-01 acceptance increment remains partial. Its existing WebSocket security
requirement was selected as a small, independent acceptance gate and completed. The public,
physical desktop and autonomous coding gates remain unchecked; no unrelated P0-02 runtime,
checkpoint, scheduling or other feature work was added in this turn.

### Changes and verified behavior

- [x] Inspect the actual WebSocket authentication route, runtime binding/limits, test fixtures,
  and architecture/gap evidence. Existing wrong-token and origin checks were present, but
  timeout/malformed-frame rejection lacked a proper close frame and replay cursors were
  coerced without an integer-range contract.
- [x] Add `tests/test_studio_socket.py`: nine tests using actual isolated Python/FastAPI/
  Uvicorn subprocesses and a real WebSocket client on random loopback ports. These require
  existing API dependencies but no model, public network or interactive desktop.
- [x] Reproduce malformed JSON causing an abnormal connection termination before the fix.
- [x] Update only the WebSocket admission path in `local_agent/studio/api.py`: malformed
  JSON/binary frames and five-second authentication timeout explicitly close with 1008;
  invalid/non-ASCII launch credentials are rejected before comparison; `after` must be an
  integer in 0..2**63-1, excluding booleans. Valid native ASCII credentials and numeric
  frontend cursors retain their existing behavior. Origins/auth/scopes remain enforced.
- [x] Verify wrong/missing/invalid credentials, malformed JSON, binary authentication,
  silent-peer timeout, invalid/oversized cursors and numeric parsing limits. Positive checks
  cover authenticated private snapshots at cursor boundaries, disconnection and continuing
  backend health. Forbidden/missing origins are denied before upgrade with HTTP 403.
- [x] Verify that test backend logs contain neither launch credentials nor the invalid-token
  canary or unhandled tracebacks. Each fixture backend and temporary database is owned by
  its test; no user conversations, installed model service or desktop applications are used.
- [x] Run the new security tests, full regression and Ruff. Test extraction lint findings
  were fixed using TestCase.enterContext and combined context managers, without exemptions.

### Fresh results

| Check | Actual result | Evidence / limit |
| --- | --- | --- |
| Existing public website acceptance | **Failed**, 1 test in 6.512s | `.runtime/p0-01-acceptance/public-browser.log`; `ERR_NETWORK_ACCESS_DENIED`. Public extraction/form checks not reached. |
| Desktop prerequisite | **Unavailable** | Read-only GetCursorPos returns Windows error 5. Physical desktop test not run; no pass inferred. |
| New real WebSocket security suite | **9 passed, no skips** in targeted run | Final expanded Unicode/cursor cases also pass in the full regression below. No mocked ASGI socket or timeout clock. |
| Full default regression | **111 unique tests: 95 passed, 16 skipped**, 31.876s | `.runtime/p0-01-acceptance/regression.log`; includes all nine new socket tests plus earlier runtime, startup, tool and policy checks. |
| Ruff | **Passed** | `.runtime/p0-01-acceptance/lint.log`; `python -m ruff check local_agent tests scripts/create-icon.py`. |
| Optional live-model/UI rerun | **Not run** | A read-only local Ollama version probe returned connection refused (10061). This gate needs no model, so no service was started and no live inference pass is claimed. |

Commands from the repository root:

```powershell
$env:LOCAL_AGENT_BROWSER_TEST = '1'
$env:LOCAL_AGENT_BROWSER_CHANNEL = 'msedge'
.\.venv\Scripts\python.exe -m unittest tests.test_live.LiveBrowserTests.test_public_websites -v
Remove-Item Env:LOCAL_AGENT_BROWSER_TEST, Env:LOCAL_AGENT_BROWSER_CHANNEL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m unittest tests.test_studio_socket -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\.venv\Scripts\python.exe -m ruff check local_agent tests scripts/create-icon.py
```

The nine added tests explain 102 → 111 unique tests. The 16 default skips remain unpassed
live/desktop/symlink checks; no enabled socket test skipped. Previous real-model/UI/build
results remain historical evidence, not fresh results for this change. No dependencies,
configuration, lockfiles, tool permissions, frontend or native code were changed; no new
installer/build claim. Restart the Studio backend to load the Python admission fix.
The first-increment source manifest remains immutable; current validation metadata and a
review patch are under `.runtime/p0-01-acceptance/`.

**Next:** complete P0-01's autonomous coding acceptance as an independent gate when local
inference is available; collect normal-session public/Notepad output for their remaining
environment gates. P0-02's second increment remains the next independent runtime feature.
Only the WebSocket gate is newly complete, not P0-01 or the entire system.

## Prior progress — 2026-10-22 (P0-02, first increment)

Selected P0-02 startup compensation after rechecking P0-01's remaining prerequisites.
`socket.getaddrinfo('example.com', 443)` still fails with error 11001; the Playwright demo
host does resolve. The read-only Windows `GetCursorPos` probe returns false/error 5.
No desktop focus/input was attempted, no DNS/security configuration was changed, and no
public/Notepad/autonomous-coding acceptance is claimed from these prerequisite probes.
P0-01's second increment remains blocked and unchecked; its local coding subcheck has
not been implemented as part of this separate increment.

### Changes and completion checklist

- [x] Inspect the current Manager/worker execution gate, Job Object ownership, Store/API
  failure paths, shared fixtures, and architecture finding R1 / feature contract F01.
- [x] Reproduce the missing startup compensation with a failing regression before the fix.
- [x] Guard startup from message recording through worker release in
  `local_agent/studio/manager.py`. An ExitStack attempts cleanup of every acquired pipe,
  process and Job Object on failure, including a process whose start partially succeeded.
  Failed process handles are reaped/closed; only this startup's owned resources are targeted.
- [x] Persist a redacted failed task/result event and surface startup errors through the
  existing authenticated API's HTTP 503 handler. Remove failed in-memory task state so a
  subsequent explicit task can start. No automatic retry/replay was introduced.
- [x] Establish cancellation ownership, publish startup, and start the monitor before
  sending the execution gate. A monitor created just before rollback safely exits when
  its task state has been removed, rather than raising an unhandled KeyError.
- [x] Add `tests/test_studio_startup.py`: real spawned-process fault injection, pipe/handle/
  monitor cleanup, no model/tool execution during injected pre-gate failures, one durable
  result, redaction, API failure visibility and successful explicit retry.
- [x] Run targeted startup checks, full regression, live local-model Studio checks and Ruff.
  Update only the completed P0-02 first-increment checkbox; preserve the remaining gates.

The ten startup tests cover process start, failure immediately after real process creation,
Windows Job Object setup, initial start-send, monitor start, pipe creation, Process constructor,
user-message recording, startup-event publication, and authenticated API reporting. All
tested startup failures settle in under five seconds with SQLite available. The send failure
also verifies that a real started monitor exits without an unhandled thread exception.
Faults are injected before delivery of the execution gate; no claim is made that an already
delivered command or completed side effect can be undone.

### Fresh verification

| Check | Actual result | Scope / evidence |
| --- | --- | --- |
| `python -m unittest tests.test_studio_startup -v` | **10 passed, no skips**, 5.299s | New fault/API checks with actual gated worker processes, not only mocked cleanup calls. |
| `python -m unittest discover -s tests -t . -v` | **102 tests: 86 passed, 16 skipped**, 17.607s | Includes existing real runtime/spawn/API/approval/coding regressions and discovery guards; `.runtime/p0-02-startup/regression.log`. |
| `LIVE_STUDIO=1` with `python -m unittest tests.test_studio.StudioLiveTests -v` | **3 passed, no skips**, 5.611s | Actual existing Ollama 0.40.7: context/stream metrics, read-tool/report and cancellation; `.runtime/p0-02-startup/live-studio.log`. |
| Ruff: `python -m ruff check local_agent tests scripts/create-icon.py` | **Passed** | `.runtime/p0-02-startup/lint.log`. |

Use `.venv\Scripts\python.exe` from the repository root for these commands. Explicit live
checks set `LIVE_STUDIO=1` only in their test process environment. Default skips remain
unpassed: nine original live checks, three Studio live checks, one live attachment check,
two UI scenarios and one unavailable Windows symlink check. The three Studio checks were
separately enabled and passed; the remaining default skips are not new verification.
Discovery still reports unique IDs/implementations; the ten new tests explain 92 → 102.

Initial fault-test instrumentation attached Mock methods to a Process instance, which Windows
spawn then tried to pickle. Corrected the test harness to patch class methods with autospec;
phase assertions now prove each injected fault reaches its intended startup stage. The final
tests create/reap real workers without those pickling errors. The existing Starlette/httpx
deprecation warning remains unrelated and no dependencies were changed.

Application change scope is one startup path plus a rollback-safe monitor lookup. No tool
policy, approvals, model settings, configuration/lockfiles, worker tool loop, frontend/native
code or installed services were changed. Existing Ollama was reused, not restarted or
terminated. The P0-01 manifest/source archive remains a point-in-time snapshot; this
increment's patch, validation metadata and prerequisite observations are retained under
`.runtime/p0-02-startup/`. Historical architecture/gap documents remain dated audit records.

Limitations: startup result writes still use the existing Store operations, so an unavailable
database can prevent durable failure recording. Atomic terminal updates and storage/monitor
exception reconciliation are P0-02's second increment, not silently claimed here. Heartbeats,
task deadlines, durable replay pagination and native/installer acceptance also remain open.
No new frontend/Rust/installer build was needed or claimed for this Python-only change.

**Next actionable increment:** P0-02's second increment—atomic terminal task/message/event
updates, monitor/pipe/storage/cancellation exception handling and phase-aware readiness/
heartbeat/deadlines. Revisit P0-01's blocked acceptance when public DNS and an unlocked
interactive desktop are available. Only the startup-compensation increment is complete.

## Prior acceptance baseline — 2026-10-22 (P0-01, first increment)

This section supersedes older environment/blocker/count claims below. Subsequent sections
are preserved historical implementation records, including their original checkboxes and
then-current limitations; they are not the current acceptance checklist.

Scope: test discovery/fixtures and evidence documentation only. Application code, trusted
configuration, dependency manifests/locks, launch scripts and existing assertions remain
unchanged. No lifecycle, approval, memory, MCP or other roadmap functionality was implemented.

- [x] Inspect shared Studio API/process/UI setup and the actual unittest discovery graph.
- [x] Move API/process fixtures into `tests/studio_support.py` and the browser UI harness
  into `tests/studio_ui_support.py`; these are plain mixins without test methods/TestCase
  inheritance. Keep the existing empty-test workspace base unchanged.
- [x] Concrete Studio, attachment and slash suites reuse setup without inheriting unrelated
  tests. Preserve API-dependency and live-UI opt-in skip gates explicitly.
- [x] Keep both intended UI scenarios; slash acceptance now has the distinct entry point
  `SlashUITests.test_slash_commands_and_chat_attachment_management`.
- [x] Add `tests/test_discovery.py` regressions for unique IDs/implementations, undiscoverable
  fixture modules, and distinct opt-in UI scenarios. Inventory comparison retains every
  original method entry point and its scenario assertions.
- [x] Refresh README status and record exact locked versions/source hashes in
  `docs/acceptance-baseline.json`, with a local review snapshot under `.runtime/p0-01/`.
- [x] Run changed backend/discovery tests, full default regression, both live UI scenarios,
  and Ruff. First lint run caught a missing `os` import/blank line in the extracted UI
  helper; corrected before live UI verification. No lint rules or security checks disabled.

### Current status and evidence

| Check / capability | Date and result | Limits / evidence location |
| --- | --- | --- |
| Targeted discovery/Studio/attachment/slash suite | 2026-10-22: 35 tests in 8.904s; **31 passed, 4 skipped** | Fixtures use actual processes, pipes, files and API with an explicit model-protocol fixture; not a model-quality score. |
| Full default regression | 2026-10-22: 92 unique tests in 12.903s; **76 passed, 16 skipped** | `.runtime/p0-01/regression.log`; skips enumerated below. |
| Live UI and enabled discovery checks | 2026-10-22: 5 tests in 30.193s; **5 passed, no skips** | `.runtime/p0-01/ui.log`; both UI scenarios use real React/API/SQLite/workers/Ollama, with only native connection IPC bridged. |
| Ruff | 2026-10-22: passed after fixing extraction imports | `python -m ruff check local_agent tests scripts/create-icon.py`. |
| Local model/GPU/tool/vision/local browser | Prior 2026-10-22 architecture audit: **11/12 live tests passed** | Carried forward, not rerun as a full live suite here; actual Qwen browser/title/write/readback passed. |
| Public web | Prior audit's twelfth live test failed DNS | `ERR_NAME_NOT_RESOLVED`; public form not reached. Not retested for this increment. |
| Build/dependency availability | Prior audit: TS/Vite/Rust checks passed; current debug EXE and installed model/API packages confirmed | No new frontend/Rust/installer build; application source unchanged. |
| Physical desktop / native lifecycle / installed app | **Unverified** | Notepad typing/saving, UIA controls, native capture/picker/clipboard/export, lifecycle and frozen-worker/NSIS acceptance remain open. |

Commands run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_discovery tests.test_studio tests.test_studio_features tests.test_slash_commands -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\.venv\Scripts\python.exe -m ruff check local_agent tests scripts/create-icon.py
$env:LIVE_STUDIO_UI = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_discovery tests.test_studio_ui tests.test_slash_ui -v
Remove-Item Env:LIVE_STUDIO_UI -ErrorAction SilentlyContinue
```

Suite accounting: previously 107 executions represented 88 method implementations. Removing
18 accidental imported/inherited API/process reruns leaves 89 scenario executions. The two
intentional UI runs retain all checks but now have separate methods. Three new discovery
regressions produce **92 IDs and 92 distinct implementations**, with zero duplicates and
no missing original method entry points. Counts do not imply 92 independent capabilities.
All 16 default skips remain explicit: nine original live checks, three Studio live checks,
one live attachment check, two live UI scenarios and one unavailable Windows symlink test.
The two UI scenarios were separately enabled and passed; the other 14 were not enabled/
available in this increment's default run. No skipped case is included in passed counts.

Environment/locks: Windows, Python 3.12.14; `uv.lock` format 1/revision 3, npm lock format 3,
Cargo lock format 4. Locked Python direct dependencies: FastAPI 0.159.1, httpx 0.28.1,
Pillow 12.3.0, Playwright 1.64.0, psutil 7.2.2, PyAutoGUI 0.9.54, PyInstaller 6.22.3,
pywinauto 0.6.9, Ruff 0.17.1, Uvicorn 0.54.0. Frontend includes React 19.3.1,
TypeScript 5.9.3, Vite 6.4.5, Tailwind 4.3.3; Rust locks Tauri 2.12.5. Full direct
version maps, lockfile hashes, UTC capture time and test IDs are in the baseline manifest.
No dependency installation/update was necessary. Starlette emits an existing httpx
TestClient deprecation warning; tests pass and dependency migration is outside this increment.

The repository still has no commits; no Git index/identity/history changes were made.
The hash manifest and local source archive establish an inspectable snapshot without
committing unrelated user files. They are not a signed release or a replacement for future
reviewed Git history. Generated evidence/archive/logs under `.runtime/` remain ignored;
retain them locally with this baseline. Existing reports in ARCHITECTURE_REVIEW and
FEATURE_GAP_ANALYSIS describe the pre-refactor audit, not new test totals.

First-increment acceptance: unique discovery, unchanged scenario assertions/skip gates,
passing relevant/default/live-UI checks and lint, dated current-status documentation,
dependency versions and source snapshot. The broader P0-01 acceptance is still incomplete.
**Next actionable increment:** P0-01's second increment—public/interactive acceptance and
one real model-driven coding bug-fix acceptance in a disposable project. Public DNS and
an unlocked interactive desktop are prerequisites for their respective checks. Do not
mark P0-01 as a whole complete or start other roadmap implementation based on this result.

## Historical implementation records

## Slash commands and persistent goals (active)

- [x] Inspect current Studio frontend, tasks, persistence, attachments and safety boundaries.
- [x] Define a 17-command catalog, validated parsing and explicit unknown-command errors.
- [x] Add tool-free `/plan` and persistent `/goal` objective/checklist/run/status controls.
- [x] Add summary, direct approved test/diff, task-stop, model and chat-management shortcuts.
- [x] Add composer autocomplete, keyboard navigation, help and goal progress panel.
- [x] Preserve approvals, scoped execution, attachments, regeneration and restart behavior.
- [x] Test backend parsing/state/workers and real Ollama/browser workflows.
- [x] Build frontend, document syntax/limits and audit every command against current source.

### Slash-command completion audit

| Requirement | Authoritative implementation and verification |
| --- | --- |
| `/plan` without execution | Separate worker branch uses structured model output and never instantiates Tools; process and live UI tests verify no tool events or project writes, including regeneration. |
| Persistent `/goal` | Additive SQLite goal/task migration; state tests reopen the database, preserve checked steps and reject implicit replacement/completion. Real UI reload retains the goal; explicit run, status, done/undo, complete and cancel paths are tested. |
| Productive additional commands | Commands catalog includes chat/agent/browser/desktop/code/summarize/test/diff/stop/new/rename/export/model/delete/help. API tests verify each task route; live UI tests exercise summaries, model selection and all local controls. |
| Discovery and keyboard use | `/` palette, prefix suggestions, arrow/Tab/Enter/Esc, help modal and unknown-command errors; verified in browser acceptance. |
| Safety | Test and Git diff still require exact existing approvals; backend rejects unauthenticated commands and escaped paths. Goal requests do not hold the cancellation lock during model preflight. Plan-only regeneration cannot become execution. |
| Reliable stopping | Fixed submission race: `/stop` checks fresh task state and queues cancellation if a task is still starting. Browser tests cover both active and delayed-start cancellation. Completed actions are not rolled back. |
| Existing behavior | Attachment/chat browser scenario is included after the slash workflow; full regression passes. Goals use existing bounded tasks and do not claim background scheduling or checkpoint pause/resume. |
| Documentation/build | All 17 catalog entries have syntax in `docs/slash-commands.md`; README updated. TypeScript and Vite production build passed. UI screenshot: `workspace/studio-slash-goal-acceptance.png`. |

Final validation: **107 tests, 91 passed / 16 skipped**; targeted slash suite **17 passed**;
actual backend/Ollama browser acceptance passed in **23.505 seconds**. Ruff and TypeScript
passed; production frontend assets built successfully with `--configLoader runner`.
The regression run exposed zero-resolution elapsed timing in quick Windows fixture calls;
worker elapsed statistics now use `perf_counter`, and affected/full tests passed afterward.
Native connection IPC alone is bridged in browser acceptance; no new native Windows
installer or physical desktop/browser automation claim is made for this command increment.
The desktop app must be fully restarted to load new backend routes and SQLite migrations.

## Chat management and attachments (2026-10-22)

- [x] Add rename, title search, Markdown export and confirmed deletion controls.
  Deletion atomically removes chat messages, attachments, tasks and events; active tasks
  block deletion. Tool audit records remain independent of conversation history.
- [x] Store bounded attachments in SQLite with message binding and ownership checks.
  File picker, drag/drop and clipboard image paste transfer explicitly selected bytes;
  no uploaded filename selects a server filesystem path or expands agent file scopes.
- [x] Support UTF-8 text/code and PNG/JPEG/WebP. Bound incoming files to 5 MiB, text to
  64 KiB, images to 20 MP; resize to 1600px and re-encode without metadata, <=2 MiB.
  Four attachments per message, eight images across model conversation history.
- [x] Add pending attachment removal and previews, persisted message attachment chips,
  multimodal model context, attachment-aware regeneration, and vision-capability checks.
  Treat attachment contents as untrusted data. Oversized text context is rejected before
  starting a task. PDF/Office parsing is explicitly unsupported.
- [x] Add authenticated, explicitly confirmed main-screen capture with preview before send.
  Native Windows capture is unit-tested with a controlled image, not claimed interactively
  verified. Region screenshots can be pasted with Win+Shift+S then Ctrl+V.
- [x] Update WebView2 drag-drop configuration for HTML5 drops, verified against installed
  Tauri schema. Preserve all existing filesystem, tool and command approval boundaries.
- [x] Live Ollama attachment test passed: actual model recognized attached red image and
  read the exact marker from an attached text file in the same conversation.
- [x] Browser E2E passed: real frontend/backend/SQLite/worker/Ollama, file upload/model
  response, text/image preview, synthetic clipboard paste/drop events, pending removal,
  Markdown download, capture cancellation, rename, title search and confirmed deletion.
  Native connection IPC alone is bridged to an isolated backend for browser acceptance;
  native file dialogs, physical clipboard and desktop capture still need manual validation.
- [x] TypeScript check and Vite production build passed (`--configLoader runner` avoids
  esbuild parent-folder access restrictions in this managed session). Ruff passed.
- [x] Full regression before final API boundary additions: 88 tests, 73 passed / 15 skipped.
  Final API boundary suite: six passed, including vision-model rejection and upload-size
  limits. A follow-up UI guard prevents late responses repopulating a switched/deleted chat.
- [ ] Validate capture/clipboard/drop/export inside the restarted native Tauri application;
  no new Windows installer was built for this increment.

## Potential optimization benefits evaluated (2026-10-22)

- [x] Inspect idle task/service state and consult official Ollama configuration documentation.
- [x] Compare three unloaded/resident pairs through the working service: median first token
  2.437s vs 0.063s; full response 4.984s vs 2.610s. Generated-token speed stayed ~75/s.
- [x] Verify `keep_alive=15m` yields an expiry ~900 seconds ahead; restore initially unloaded state.
- [x] Compare current/concise planning on real readback and bug-review workflows: 8/8 passed;
  concise prompt slowed readback ~42% and improved bug review ~7% in two samples each.
  No global planning change justified.
- [x] Attempt isolated Flash Attention/f16/q8_0 profiles without restarting the primary service.
  Model requests blocked with HTTP 500 Access is denied. Flags alone are not treated as proof
  that an optimization works. No tuning defaults applied.
- [x] Fix evaluator context-manager exception handling; regression verifies propagation and
  cleanup of owned server processes. Ruff passed; evaluator regression passed.
- [x] Record measured benefits, artifacts, limitations and exact rerun steps in
  `docs/optimization-benefits.md`.
- [ ] Complete Flash Attention/cache comparisons in the normal Windows session; test smaller
  models and broader agent tasks before changing production defaults.

## Model performance evaluation (2026-10-22)

- [x] Audit current model, GPU residency, saved context/temperature and token metric formula.
- [x] Add a repeatable local benchmark with task-idle checks, per-request timings,
  authoritative token counts, exact quality checks, incremental JSON reports and restoration.
- [x] Run 27 short-prompt measurements across 4K/8K/32K (three repeats) and 16 measurements
  across 8K/32K with 7,541-token retrieval inputs (two repeats). 30/30 scored checks passed.
- [x] Run live structured/GPU, file-tool and vision acceptance: three passed in 4.737 seconds.
- [x] Validate benchmark guard/summary and existing metric edge cases: five tests passed.
- [x] Final regression: 67 tests, 54 passed / 13 skipped; Ruff passed.
- [x] Confirm original 32K loaded context restored and persistent preferences unchanged.
- [x] Document results, metric limitations and measured settings decisions in
  `docs/model-performance.md`. Measured speed ~75 tokens/s; no context-related speed
  improvement demonstrated. 8K saves ~680 MiB model VRAM versus 32K.
- [ ] Broader coding/browser workloads, full-window quality, cold starts, concurrent load,
  alternative models/quantizations, server optimizations and temperature sweeps were not
  evaluated; conclusions are limited to the documented tests.

## Fixed desktop tasks stuck at “started” (2026-10-22)

- Inspected the user's task records: repeated starts/cancellations with no worker events.
  Ollama returned a counter plan in 3.95 seconds; a direct live agent read/tool test passed.
- Reproduced the stall through the actual `local_agent.studio.runtime` subprocess and
  authenticated FastAPI task endpoint, with stdin/stdout pipes matching the desktop launcher.
  The task failed to finish within 35 seconds even with an immediate local model fixture.
- Root cause isolated to the Windows parent shutdown watcher blocking on stdin. Replacing
  that read with `PeekNamedPipe` polling let spawned Python workers initialize and execute.
  The same regression then completed in about 1.4 seconds. Shutdown requests still exit cleanly.
  Reference: https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe
- Added worker-ready, planning and next-action progress events. Added an optional runtime
  port argument for isolated tests; the desktop still defaults to loopback port 17861.
- Removed temporary stack-dump instrumentation after diagnosis. No user task or model files
  were modified. Test subprocesses/workspaces are isolated and cleaned up.
- Full suite: 65 tests, **52 passed / 13 skipped**. API tests now pass with installed
  dependencies. Ruff passed. Runtime test uses a protocol fixture and real process/API/tools;
  it does not certify a complete model-generated counter project. The live service became
  unavailable later in this session, so that complete counter workflow remains to be retried
  after restarting the desktop app. New backend code requires a full app restart.

## Response generation statistics

- [x] Capture Ollama `eval_count` and `eval_duration` from final streamed and non-streamed
  responses; calculate tokens/second as generated tokens / generation nanoseconds * 1e9.
  Reference: https://docs.ollama.com/api/chat . Streaming chunk counts are never token counts.
- [x] Display generated tokens, generation speed and elapsed seconds below new completed
  assistant responses. Agent workflows show task totals across measured model calls; speed
  is weighted by generation time, not an average of individual rates. Elapsed time includes
  loading, prompt processing, tools and approval waits, but excludes process startup.
- [x] Save statistics with messages using an additive SQLite migration. Historical messages
  without statistics remain readable. Missing statistics and cancelled runs show no invented
  rate; zero generation duration displays speed unavailable.
- [x] Validate migration/persistence, streamed metadata propagation, multi-call aggregation,
  missing/zero timings and premature stream termination. 21 targeted tests passed;
  Ruff and TypeScript `tsc --noEmit` passed.
- [ ] Live Ollama/desktop visual validation for this addition: local service probe returned
  connection refused in this session. Existing live test now asserts positive reported usage.
  Restart the desktop app/backend to load the change, then send a new message.

## Latest desktop launch recovery

- User reports all three Studio live tests passed in 8.716 seconds in their normal
  Windows session. The earlier model access blocker does not reproduce there.
- User's desktop launch reached Vite/Rust compilation but Vite failed with EBUSY watching
  `desktop/src-tauri/target/debug/deps/local_agent_studio.exe`.
- Added the official Tauri Vite watcher exclusion `**/src-tauri/**`. Rust source watching
  remains Tauri's responsibility; frontend watching remains enabled.
- Desktop launch acceptance still requires a successful restart after this correction.
- TypeScript `tsc --noEmit` passed after the change. Vite build was attempted but esbuild
  cannot read the parent directory in the managed session (Access is denied); this is
  separate from the user's EBUSY error. Full build validation must run in the normal session.

## Desktop application implementation (active)

### Audit and target architecture

Read AGENTS.md, this history, application modules, tests, scripts and documentation.
Reuse Agent/Tools/Policy/Ollama; preserve launch.ps1 and existing CLI behavior.
Add a FastAPI loopback service with bearer authentication, authenticated WebSocket events,
SQLite conversations/tasks, and one owned worker process per task. React/TypeScript with
Tailwind runs inside Tauri 2. Rust owns backend startup and passes an ephemeral credential
over environment/IPC, never a URL. Windows Job Objects own task descendants. GUI approvals
are scoped to one pending task/action. No pause/resume claim: the existing loop has no
safe persistent checkpoint format. Authentication intervention is an explicit live wait.

### Checklist

- [x] Audit reusable components, configuration, dependencies and existing test evidence.
- [x] Review official Tauri, FastAPI/WebSocket and Tailwind integration documentation.
- [x] SQLite conversations, messages, settings and task/event persistence; tested.
- [x] Implement streaming contextual chat, regeneration, cancellation and model selection.
- [x] Implement process-isolated tasks, progress, action approvals and emergency stop.
- [x] Integrate browser workspace, screenshots/download results and authentication intervention.
- [x] Integrate desktop workspace, launch shortcut, screenshots and permission display.
- [x] Integrate coding workspace, scoped directory selection, file viewer, edit review and output.
- [x] Implement Ollama detection/start, inventory/load state and optional resource telemetry.
- [x] Implement authenticated FastAPI routes, WebSocket replay and scoped file access.
- [x] Implement Tauri lifecycle, single instance, startup errors, restart and child cleanup.
- [x] Implement React/Tailwind chat and workspaces; rendering/compilation still unverified.
- [x] Test backend core regression, real worker approval handling and SQLite persistence.
- [ ] Execute API security/WebSocket tests (dependencies absent).
- [ ] Pass live Studio model/chat/tool workflows (model store access denied).
- [ ] Frontend build, desktop end-to-end validation and Windows installer.
- [x] Development/production launch, acceptance and troubleshooting documentation.

Checked implementation boxes above mean source exists, **not** that GUI acceptance passed.
There is no simulated production data or mock execution path in the application.

### Current build blockers

Node/npm, Rust/cargo and Visual Studio build tools were not found on PATH or their checked
standard locations. FastAPI/uvicorn/httpx/psutil/PyInstaller are absent in .venv.
Attempted uv pip installation failed fetching PyPI with Windows socket error 10013.
No application build or installer is claimed until real compilation and validation pass.

### Verification on 2026-10-21

- `python -m unittest discover -s tests -t . -v`: 60 tests, 44 passed, 16 skipped.
  Skips: nine pre-existing opt-in live tests, one unavailable symlink test, three API
  tests (FastAPI/httpx absent), three opt-in Studio live tests.
- `python -m ruff check local_agent tests scripts/create-icon.py`: passed.
- PowerShell parser checks passed for setup-desktop.ps1, desktop-dev.ps1 and
  build-desktop.ps1. Missing-backend-dependency startup returned a structured uvicorn error.
  The test-owned Ollama service was stopped after diagnosis. This folder has no `.git`
  metadata, so repository-wide Git diff/status inspection was unavailable.
- Python compilation passed. New worker tests exercise actual spawned processes,
  Windows Job Objects, approval IPC, real file writes, denial, replay rejection,
  streamed HTTP protocol parsing and persistence. Their inference server is an explicit
  test fixture; they do not certify local model intelligence or GUI behavior.
- `LIVE_STUDIO=1` suite: cancellation passed; contextual chat and real tool workflow failed.
  Initially no Ollama listener existed. Started the existing portable Ollama with local-only
  settings; CUDA detected RTX 4070 Ti, 12 GiB. `/api/tags` then returned no models and
  `/api/chat` returned HTTP 500 `Access is denied`. Server log identifies manifest access
  failure. Existing manifests are present. No model files or access permissions were changed.
- Original CLI tests remain passing. Historical real-model results below are previous-run
  evidence, not evidence that this managed-session inference attempt succeeded.
- API HTTP/WebSocket security tests are written but skipped. Frontend, Rust lifecycle,
  interactive browser/authentication, Notepad UI, packaged worker spawning and installer
  remain untested. No UI screenshot or installer is presented as a verified deliverable.

### Desktop requirement review

| Requirement | Source implementation | Verification / remaining work |
| --- | --- | --- |
| Chat streaming, Markdown/code, history, conversations | React chat + Ollama NDJSON + SQLite | Protocol/persistence passed; live model and UI blocked |
| Stop, regenerate, copy, model selection, context | Worker cancellation, regenerate request, clipboard, settings | Cancellation passed; other UI interactions pending |
| Start/progress/errors/approvals/plans/results | Manager/worker events and activity panel | Real IPC/tool approval tests passed; HTTP/UI pending |
| Pause/resume only with checkpoints | Explicitly unavailable | Correctly omitted; no checkpoint claim |
| Browser navigation/actions/previews/downloads | Existing Browser adapter, event history and image previews | Prior adapter evidence retained; GUI/live auth pending |
| Authentication and submission approval | Headed browser intervention + nested approvals | Implemented, not interactively validated |
| Desktop launch/input/previews/stop/permissions | Existing Desktop adapter, shortcut and policy display | Adapter regression passed; interactive Notepad pending |
| Project selection/files/diffs/tests/output | Scoped API, file viewer, tool events and edit approval | Real file review/denial passed; UI and API pending |
| Ollama models/loading/resources/settings | Tags/ps, optional psutil/nvidia-smi, SQLite preferences | GPU detected; models inaccessible in this session |
| Automatic backend/model startup | Tauri child ownership + model start/connect | Source only; requires compiled Tauri and API packages |
| Duplicate prevention/shutdown/crash recovery | Single-instance plugin, exclusive socket, Job Objects, interrupted status | Worker cancellation/recovery tested; full lifecycle pending |
| Dark responsive navigation/workspaces/history | React/Tailwind/CSS | Not rendered or compiled; visual acceptance pending |
| Loopback/auth/scope/approvals/log sanitization | Bearer token, origins, policy, redacted events, no shell endpoint | Policy/core tests passed; API security tests blocked |
| Setup/build/installer/dependency management | PowerShell scripts, Python extras, npm/Cargo manifests | Install blocked; new lockfiles and NSIS package pending |
| README/examples/troubleshooting | docs/desktop.md and README updated | Complete documentation; remaining steps explicit |

### AGENTS.md review for this increment

1. Target remains Windows/local-only; existing GPU/model installation reused.
2. Existing Agent/Tools/Policy architecture audited; official framework docs consulted.
3. Model remains configurable. Historical inference/tool/vision evidence preserved; current
   session model access failure is an external blocker, not a passing result.
4. Browser/desktop/coding adapters reused; existing bounded recovery retained. GUI-specific
   integrations await interactive validation.
5. One desktop interface implemented in source; working integrated desktop acceptance pending.
6. Existing scopes/approvals/audit/emergency stop retained; ephemeral API authentication added.
   New files also require review in Studio. No unrestricted admin access or process-wide kills.
7. Ordinary dependency installation attempted, blocked by network restriction; existing
   projects/configuration untouched. No security controls bypassed.
8. Regression and worker tests executed; live model tests failed with a diagnosed external
   access blocker. Public browser and interactive Notepad requirements remain open.
9. Launch/config/dependency/setup/examples/troubleshooting/tests/checklist delivered as source.
   A verified desktop executable and installer are **not delivered**.
10. Work proceeded incrementally through implementation and testing; remaining blockers and
    exact recovery/acceptance steps are in `docs/desktop.md`.

## Latest command-approval diagnosis

The user's first-task retry failed before showing approval, but the old report discarded
the specific Denied detail. The exact historical arguments cannot be recovered from the
content-free audit log. Unknown command profiles and invalid paths can both fail before
approval; neither should be described as a confirmed user rejection.

Added configured command-name enums and workspace-relative cwd guidance to tool schemas.
Blocked reports and console output now retain redacted error details. Policies and the
requirement to type APPROVE remain unchanged.

- [x] Ruff passes; core suite: 48 discovered, 38 passed, 10 explicit skips.
- [x] Real-model dry run of the user's exact objective reached execute_code approval with
  the correct unittest argv and workspace/first-task directory. The diagnostic deliberately
  denied approval without running project code; project test results are not claimed.

## Latest lint review

Reviewed `a local diagnostic export`: Ruff reported 25 findings,
including 18 safe automatic fixes. Fixed import ordering and regex naming, narrowed
diagnostic/Windows API exception handling, made subprocess exit handling explicit,
used TypeError for invalid tool argument types, and gave background-process temporary
files an ExitStack-managed lifetime. Two intentional adapter/CLI exception boundaries
retain narrowly documented BLE001 exemptions so errors remain redacted and normalized.
No project-wide lint rules were disabled.

- [x] `.venv\Scripts\python.exe -m ruff check local_agent tests`: All checks passed.
- [x] Core regression suite: 46 discovered, 36 passed, 10 explicit skips.
- Live desktop and network-dependent tests were not rerun for this lint-only update.

## Latest update: diagnosis of the supplied validation log

This section supersedes earlier environment snapshots and test counts below.
The user's `local validation transcript` shows successful installation,
model/GPU/vision/tool tests, and three failures: public DNS, Notepad window discovery,
and an empty model response in the unified workflow.

- [x] Dependencies and Python 3.12 are installed; doctor now succeeds. uv.lock and requirements-installed.txt exist.
- [x] Qwen3.5 9B Q4_K_M, structured output, tool execution and vision pass real tests.
- [x] GPU allocation verified: size_vram = 5,862,210,928 bytes, context = 8192.
- [x] Fixed unified execution by explicitly asking the model to execute its plan; added bounded recovery for empty responses. The real browser/title/write/readback workflow now passes.
- [x] Fixed premature Notepad window lookup: wait for a new visible verified executable window, support Store handoff, exclude hidden IME/tooltips and existing documents, pin the selected handle and owned dialogs. Classic Notepad uses deterministic Win32 controls; Store applications use UIA.
- [x] Core regression run: 46 discovered, 36 passed, 10 explicit skips.
- [x] Separate real-model suite: all 4 tests passed, including combined browser/file coordination.
- [ ] Full Notepad type/save/readback still needs an interactive-terminal rerun. Here launch/window discovery now succeeds, then SetCursorPos fails with "There is no active desktop required for moving mouse cursor". Store handoff selection is unit-tested, not live-validated.
- [ ] Public example.com browsing remains blocked by DNS. Resolve-DnsName also reports DNS_ERROR_RCODE_NAME_ERROR; no DNS/security settings were changed.
- [x] Ruff findings resolved; see the latest lint review above.

Next user-side check: save work and close unused Notepad windows, then run
`.\scripts\validate.ps1 -Desktop` from the unlocked desktop PowerShell terminal.
The pywinauto SyntaxWarning in the supplied log was not the cause of the failure.

## Requirements checklist

- [x] Read AGENTS.md and inspect workspace: no existing implementation.
- [x] Inspect Python, Git, GPU and installed tools.
- [x] Consult official Ollama, Browser Use, Playwright, PyAutoGUI, pywinauto and Aider documentation.
- [x] Select initial architecture and document compatibility decisions and alternatives; desktop/model selection remains provisional until live validation.
- [x] Isolate and install dependencies; configure local Ollama and Qwen3.5 9B.
- [x] Verify inference, GPU allocation, structured output, tool calls and vision.
- [x] Implement browser adapter; local navigation, clicks, forms, extraction, downloads and tabs verified. Public network remains blocked.
- [x] Implement desktop adapter for approved launches, UIA, screenshots and input; all live desktop capabilities remain unverified.
- [x] Implement coding tools and verify real edit/test/fix cycle, staging, reviewed commits and Ruff lint.
- [x] Implement unified controller and natural-language CLI; real model browser/file coordination now verified.
- [x] Implement permission checks, untrusted-data separation, content-free audit log and emergency stop; residual security limits documented below.
- [x] Automated safety and orchestration tests.
- [ ] Practical browser, Notepad, coding and combined-category acceptance tests.
- [x] Launch scripts, configuration, dependency declarations, setup, examples, troubleshooting and extension documentation.
- [x] Final requirement-by-requirement audit with verified results and explicit limitations.

## Original environment evidence (historical; see latest update)

Windows PowerShell 5.1; Python 3.14.7; uv 0.12.18; Git available.
NVIDIA RTX 4070 Ti, 12,282 MiB VRAM, driver 616.56; initial GPU usage 714 MiB.
Ollama, Node and npm are absent from PATH. No Git repository or source files existed beyond AGENTS.md.
WMI operating-system inspection returned Access denied in the managed execution environment.
Filesystem writes are limited to this workspace and temporary directories; network access is restricted.
Further inspection: Windows build 26200; approximately 474.9 GiB free disk space.
System Python includes Playwright 1.63.0, and Microsoft Edge is installed. No downloaded
Playwright Chromium exists. The isolated `.venv` uses available Python 3.14.7 and has no
automation packages. Python 3.12 is the intended setup target, not an installed runtime.

## Plan

1. Resolve dependency availability and choose a small unified controller with maintained automation libraries.
2. Build policy enforcement first, then local model, browser, desktop and coding adapters.
3. Add bounded orchestration, CLI, diagnostics and stop controls.
4. Run unit tests and opt-in integration checks; repair failures and record actual evidence.
5. Audit every requirement and document genuine external blockers without claiming untested success.

## Earlier blocked-state report (historical; see latest update)

### Follow-up verification and recovery guide

Rechecked after the request to complete the checklist: outbound PyPI access still fails
with error 10013; the local model endpoint still refuses connections; isolated automation
packages remain absent; native UI Automation still enumerates zero accessible windows.
The core suite was rerun: 38 discovered, 28 passed, 10 explicitly skipped, no failures.
These unchecked requirements cannot truthfully be marked complete in this environment.

See [docs/recovery.md](docs/recovery.md) for numbered remediation steps, exact commands,
pass criteria, and a mapping from every remaining requirement to its recovery step.
Network/desktop access will enable testing; it does not guarantee that currently untested
model/desktop compatibility or the documented security limitations are resolved.

Core, adapters, CLI, tests and documentation are implemented. Live model installation,
interactive desktop compatibility and autonomous end-to-end acceptance cannot be completed
in this managed session. No inference/GPU/tool-reliability claims are made from mocks.
AGENTS.md was preserved unchanged.

## Test results (2026-10-21)

| Check | Actual result |
| --- | --- |
| `.venv\Scripts\python.exe -m unittest discover -s tests -t . -v` | 38 discovered: **28 passed, 10 skipped**, no failures |
| Real local browser fixture suite, system Python + Edge | **3 passed**: navigation/forms/tabs/download, denied POST, browser-to-file dispatch |
| Public browser test | **Failed/blocked**: `net::ERR_NAME_NOT_RESOLVED` for example.com |
| Live model structured-output/GPU probe | **Failed/blocked**: connection refused at 127.0.0.1:11434, Windows error 10061 |
| Live Notepad test | **Failed/blocked** before launch: `ModuleNotFoundError: pywinauto` |
| Native Windows UI Automation alternative | Assemblies load; zero accessible top-level windows in this execution session |
| Python source compilation | Passed for local_agent and tests |
| PowerShell syntax parsing | Passed for launch, stop and scripts/*.ps1 |
| Ruff | Not installed; lint check untested |

The 10 default skips comprise nine explicit live-integration opt-ins and one symlink test
because Windows symlink creation is unavailable. The three local browser tests were run
separately and passed; they are not live-LLM tests. Hardlink denial is tested successfully.
Model tool calling, vision and model-driven unified acceptance have test implementations
but remain unrun against a real model.

### Failures diagnosed and corrected

- A real temporary Git repository was initialized. A deliberately wrong addition function
  failed its test. The adapter overwrote it after approval, reran the test successfully,
  compiled the project, and read Git status/diff. This validates deterministic coding
  primitives, not autonomous LLM debugging.
- The initial supervisor cancellation path took approximately 10 seconds while an HTTP
  inference call was blocked. Replaced `taskkill` supervision with a Windows Job Object.
  The regression test now terminates the blocked worker in under one second and passes in
  the final suite. Task-local processes and command timeouts have separate passing tests.
- Reviewed pywinauto's source and replaced the assumed UIA `has_focus()` call with a native
  foreground-window check. Actual desktop behavior still requires an interactive session.

## Requirement-by-requirement audit

### 1. Target hardware and local operation

- [x] Confirm Windows, GPU and driver; inspect Python/Git/uv and disk availability.
- [x] Enforce loopback-only inference endpoint, no proxies or redirects, no cloud fallback.
- [ ] Verify runtime acceleration and memory/performance on the stated GPU: no model installed.
- CPU/RAM specifications are user-supplied; WMI inspection was denied. They were not independently verified.

### 2. Research and architecture

- [x] Review official Ollama, Browser Use, Playwright, PyAutoGUI, pywinauto, Aider, uv and Windows Job Object documentation.
- [x] Evaluate Browser Use and Aider's Ollama integrations; document why direct maintained library adapters keep one policy boundary.
- [x] Investigate native .NET UI Automation as a dependency-free alternative; inaccessible desktop prevents validating that alternative here.
- [x] Record architecture, evidence and official references in docs/architecture.md.
- [ ] Establish actual model/desktop framework compatibility: externally blocked, not inferred from documentation.

### 3. Local model

- [x] Verify official `qwen3.5:9b` tag and advertised vision/tool support.
- [x] Implement local Ollama chat, native tool calls, structured planning and image observations.
- [x] Configure initial context 8192, temperature 0.1, one parallel request/loaded model and bounded output.
- [ ] Install Ollama and download model weights: blocked by network policy.
- [ ] Verify model loading, GPU allocation, JSON adherence, real tool execution and vision.
- [ ] Benchmark smaller/alternative quantized models or optimize based on measurements; requires working inference first.

### 4A. Browser automation

- [x] Isolated browser context; local navigation and link clicks verified.
- [x] Fill harmless local form without submission; extract body text/title/links.
- [x] Download into scoped new file and verify bytes; multiple named tabs verified.
- [x] Preserve tabs and controller task history; failure budgets and read-only navigation retry implemented.
- [x] Verify denied POST never reaches local fixture server.
- [ ] Public-site validation and autonomous browser reasoning: DNS/model blockers.
- Browser PNG screenshot creation is verified; screenshot-to-model interpretation remains untested.

### 4B. Windows desktop automation

- [x] Implement allowlisted app launch, UIA inspection/control, per-action confirmations, mouse/keyboard fallback and screenshots.
- [x] Implement scoped file primitives shared with desktop workflows.
- [ ] Install desktop packages and validate real app/control/menu/screenshot/input behavior.
- [ ] Run Notepad type/save/readback to completion. Store Notepad process handoff may require adaptation; no successful launch is claimed.

### 4C. Coding/development

- [x] List/read/create/modify scoped project files with overwrite review.
- [x] Execute configured commands with approval, timeout and stop handling.
- [x] Verify real failing-test/correction/passing-test/build cycle in temporary Git repository.
- [x] Implement background command profiles with cleanup; verify start/stop.
- [x] Git init/status/diff/staging/commit verified, including staged-diff review before commit. Test identity was configured only in the disposable repository.
- [ ] Exercise lint; no root Git repository or global identity was configured.
- [ ] Validate model-driven repository understanding/debugging, beyond deterministic tool orchestration.

### 5. Unified interface

- [x] One CLI accepts natural-language objectives; no manual switching between adapters.
- [x] Structured plan, sequential actions, observed results, context limits, bounded recovery and final report implemented.
- [x] Mocked-model planning/action/readback and failure-budget tests pass.
- [x] Deterministic browser-to-file integration passes across two categories.
- [ ] Actual local-model interpretation/coordination/verification acceptance: no inference service.
- Reports explicitly separate model statements from action evidence; a model's final prose is not independently certified as correct.

### 6. Safety and permissions

- [x] Reject traversal, device/stream paths, credential stores and hardlinked files.
- [x] Deny unknown tools, malformed arguments, unconfigured commands and browser origins.
- [x] Confirm overwrites, code execution, Git operations, browser interactions, network mutations and desktop input.
- [x] External content is tagged untrusted and cannot directly change configuration or supply approval.
- [x] Audit attempts/results without raw arguments or outputs; redact common secret patterns from console/model observations.
- [x] Stop latch, Ctrl+C supervision, Windows Job Object lifetime, command timeouts and PyAutoGUI fail-safe implemented; supervisor/command cancellation tested.
- [x] No administrator request, security-control change or unrestricted execution mode added.
- [ ] Complete prompt-injection resistance is not established. Logical policy is not an OS sandbox; approved code/desktop actions run with user permissions, allowed GET requests can have side effects, and concurrent filesystem mutation remains a limitation.
- Screenshot observations can remain after crashes; logs omit raw screenshots and content. Secret redaction is best effort, not a credential detector.

### 7. Installation/integration

- [x] Inspect before installing; create isolated .venv and workspace-local setup scripts.
- [x] Attempt Python 3.12 download with uv: failed after retries with socket permission error 10013.
- [x] Attempt dependency installation: no reachable package candidates; direct PyPI request confirms error 10013.
- [x] Use existing system Playwright/Edge for independent local browser validation without changing global packages.
- [ ] Complete dependency installation, resolve/lock package versions, install Ollama and pull model.
- No pre-existing project/configuration was overwritten, and no policy bypass was attempted.

### 8. Required acceptance tests

- [ ] Real model loads/GPU/tools: blocked.
- [ ] Public website/navigation/form: blocked; equivalent local browser fixtures pass.
- [ ] Notepad launch/type/save/readback: blocked.
- [x] Real temporary Git repo/function/tests/bug correction/readback: passes.
- [ ] Autonomous multi-category task: blocked; deterministic integration passes.

### 9. Deliverables

- [x] Implementation modules under local_agent/ and automated tests under tests/.
- [x] launch.ps1, stop.ps1, setup/start-model/pull-model/validate scripts.
- [x] agent.toml and pyproject.toml.
- [x] README setup, examples, model changes, troubleshooting and extension instructions.
- [x] Architecture/source notes and this verification/limitation report.
- [ ] Fully installed and verified working local agent; generated dependency lockfile.

### 10. Execution rules and remaining work

Implemented incrementally, ran tests, diagnosed failures, corrected the cancellation bug,
researched alternatives and preserved explicit evidence. Remaining work depends on external
network access and an interactive desktop, rather than further speculative code generation.

1. In an authorized network-enabled environment, run scripts/setup.ps1 and preserve uv.lock.
2. Start the local server, pull qwen3.5:9b and run live model/GPU/tool/vision acceptance tests.
3. Run public browser and real model-driven combined workflow tests.
4. Run desktop acceptance in an unlocked interactive session; resolve any Store Notepad process handoff.
5. Run Ruff and remaining desktop checks, benchmark settings, then update this audit with actual results.

No permission question was raised because the session's managed policy cannot grant a
network/sandbox escalation. Completion requires an environment that permits the documented
installation and desktop operations; additional user credentials are not currently needed.
