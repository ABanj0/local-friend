# Development Roadmap

Publication status (2026-10-28): an opt-in Hyper-V command backend is now present in
source, with input staging, ownership leases and fail-closed dispatch. Its live isolation,
canary/network/cancellation and restart acceptance remains incomplete; P1-07 stays open.
See [execution backend scope](docs/execution-backends.md). Earlier statements that no
backend exists or host provider access is denied describe the dated stages below.

P1-07 resumed2026-10-28: actual Hyper-V management role/provider now work without a full
Administrator token. A separately identified imported execution VM has pre-boot deny-all
ACLs, Standard-user pinned-key SSH, bounded resources and sealed post-bootstrap networking.
The existing release VM remains running and unchanged. Initial probes are not full
acceptance; backend integration, clean baseline, reviewed staging, host canary/network/
cancel/recovery and regressions remain pending. Keep P1-07 unchecked. See IMPLEMENTATION.md.
Earlier provider-denied status below is historical, superseded by access-restored.json.

P0-05 third completed (2026-10-28): actual Standard-user Windows guest native controls,
real Ollama attachment reply/copy/cancel, exact184-byte export and screenshot preview pass.
The0.1.0→0.1.1 NSIS upgrade preserves all146 original logical records/configuration;
default uninstall/reinstall preserves162 current records and a new real reply succeeds.
Explicit native delete-data uninstall removes guest Studio Local/Roaming data and its
default workspace, preserving the outside project/source and independent Ollama identity.
Final owned processes/tasks/listeners are absent.54 regression tests pass,1 diagnostic is
skipped; Ruff passes. No host production/app source change. Evidence:
.runtime/p0-05-vm-acceptance/validation.json. Earlier pending release statements below are
historical. P1-07 remains separate: host Get-VM still denies access and this guest has no
implemented/enforced isolated-agent execution backend. Failed model benefit gates remain.

Guest SSH automation verified (2026-10-28): exact console SHA256 host-key match is pinned;
key-only SSH actually logs in as StudioTest with standard_user=true. New current-user
temporary key replaces the unreadable former sandbox key; obsolete guest authorization is
revoked and fresh login succeeds. Direct readback verifies installed0.1.0 native/backend
hashes, local Ollama0.40.12 with the expected9B digest, and the exact14-byte approved
artifact/hash. No password/admin login or new firewall change. P0-05 third remains open
for remaining native/upgrade/history/uninstall checks; P1-07 is not inferred. Evidence:
.runtime/p0-05-vm-ssh/guest-readonly-evidence.json and IMPLEMENTATION.md.

Managed VM SSH transport restored (2026-10-28): after owner permission change, actual
TCP22 returns the Windows OpenSSH9.5 banner and strict ssh.exe reaches unknown-host-key
verification. Earlier network-denial blocker is resolved at transport scope. Guest host
identity and key-only Standard-user authentication are pending; enrollment operator parses
and refuses the host account. No SSH login or release completion is inferred. Evidence:
.runtime/p0-05-vm-ssh/ and IMPLEMENTATION.md.

SSH transport split resolved (2026-10-28): owner normal-host TCP22 now succeeds following
the scoped rule-profile change, with source192.0.2.1. Actual managed SSH still fails
before authentication with connection Permission denied. Guest network access is ready
from normal Windows; this chat's network grant and later key/host identity verification
remain prerequisites. No further guest firewall broadening or release completion. See
.runtime/p0-05-vm-ssh/after-profile-fix.json and IMPLEMENTATION.md.

Guest SSH alternative investigated (2026-10-28): identified VM IPv4/MAC match and owner
confirms192.0.2.2/gateway192.0.2.1. Local key-only client preparation validates,
but actual TCP22 gets Windows10013 and ssh.exe exits255/connection Permission denied
before authentication. Guest SSH readiness is unknown; no server/firewall changes made.
SSH automation remains blocked on approved transport access; no native GUI or release
acceptance is inferred. Evidence: .runtime/p0-05-vm-ssh/ and IMPLEMENTATION.md.

Guest approved-file readback (2026-10-28): owner confirms the expected VM-APPROVAL-OK text
and14-byte result after the fresh-approval instructions. Actual SHA256/journal output is
not supplied; expected computed hash is not relabelled as observed. Next: seed attachment/
preference retention fixtures and collect baseline evidence before upgrade. Full guest
approval records, installed hashes, upgrade and uninstall acceptance remain open.

Guest deny-first file observation (2026-10-28): owner reports Test-Path=False following
the Agent denial instructions. Exact task denial/journal output remains uncollected;
absence alone is not a fabricated approval record. Next: fresh approval and exact guest
artifact readback. P0-05 third stays open; see IMPLEMENTATION.md.

Guest actual Chat reply (2026-10-28): owner reports the installed app returns the requested
VM-CHAT-OK marker using the local9B selection. Native connection and Chat generation are
owner-observed. Next: denied then freshly approved Agent write with independent guest
readback, followed by seeded upgrade/data acceptance. No primary release checkbox closes;
model digest/GPU and full guest acceptance are not inferred. See IMPLEMENTATION.md.

Guest installed connection (2026-10-28): owner reports Studio connected after the clean
Standard-user precheck and hash-guarded0.1.0 launch instructions. This is native owner
observation, not proof of model generation, installed payload hash or approved tool effects.
Next: actual Chat reply and denial/fresh approval/file readback, then seeded upgrade/data
acceptance. P0-05 third remains open; see IMPLEMENTATION.md.

Guest clean-account prerequisite (2026-10-28): owner explicitly confirms actual pre-install
values match StudioTest/StandardUser=true and StudioDataExists/StudioInstalled=false.
This is owner-observed evidence, not managed guest inspection. Next: guest hash verification
and normal0.1.0 installation from the scoped disc. Inference, real workflows, upgrade and
data-retention acceptance remain open; no primary release checkbox closes.

Guest model prerequisite update (2026-10-28): owner reports Ollama0.40.12 and an empty
guest model listing. Runtime installation is now owner-observed; local model/inference
and guest Studio acceptance remain unverified. Next: guest `ollama pull qwen3.5:9b`,
then retain the resulting listing and proceed with the prepared installer data disc.
No release checkbox closes; see IMPLEMENTATION.md.

Guest runtime/download and scoped transfer progress (2026-10-28): owner reports Ollama
downloaded in the VM; installation/version/model are not yet observed. Built a read-only
148,260,864-byte STUDIO_TEST data ISO with exactly two original installers, checksums,
instructions and a read-only guest account/footprint observer. All five actual ISO readbacks
match SHA256/byte counts; observer syntax passes. No credentials/history/weights/shares or
new dependencies; no VM attachment/guest installation is inferred. Next: guest Ollama
version/local9B pull, clean checkpoint, attach the data disc and verify the guest account/
empty Studio profile before installing0.1.0. P0-05 third remains open. Evidence:
.runtime/p0-05-vm-transfer/validation.json and docs/windows-test-vm.md.
Three subsequent checks confirm unchanged managed VM access denial and no guest runtime/
model results. Continuous execution is blocked pending those owner observations and VM
operations; all unverified acceptance remains unchecked. See IMPLEMENTATION.md.

Guest desktop/account progress (2026-10-28): owner confirms the named VM window, Windows
desktop and StudioTest sign-in. This supersedes the boot-failure prerequisite below; guest
group membership and actual installer/runtime acceptance remain unverified. Both retained
0.1.0/0.1.1 installers rehash correctly. Next: guest per-user Ollama setup, scoped installer
transfer and clean standard-user acceptance. No release checkbox closes. Evidence:
.runtime/p0-05-vm-guest/readiness.json and IMPLEMENTATION.md.

VM boot recovery (2026-10-28): owner reaches the firmware boot-failure summary; the VM
directory and virtual disk now exist. Managed provider inspection remains denied. Remove
the setup script's start-before-console timing hazard: newly created VMs stay off until
the owner clicks Start in the open console.11 operator/discovery tests pass,0 skipped;
Ruff/PowerShell parse pass. Preserve the existing VM and retry its DVD keypress prompt;
successful Windows Setup boot and all guest acceptance remain unverified. Evidence:
.runtime/p0-05-vm-boot/validation.json and docs/windows-test-vm.md.

VM setup operator prepared (2026-10-28): owner supplies the Windows ISO. Corrected its
duplicate .iso.iso extension; the expected Windows11.iso is now present,9,047,330,816 bytes.
scripts/new-windows-test-vm.ps1 provides one normal Administrator PowerShell command for
the documented VM configuration. Eight simulated safety contracts plus three discovery
checks pass, no skips; Ruff and PowerShell parsing pass. Actual execution fails closed on
provider Access denied before creating a VM folder. Owner must run the command in the
normal elevated session; guest setup and actual acceptance remain open. Evidence:
.runtime/p0-05-vm-setup/validation.json. Earlier missing-ISO notes below are historical.

VM prerequisite update (2026-10-28): Hyper-V commands are now installed and vmms is running.
Managed Get-VMHost/Get-VM/Get-VMSwitch return Access denied; no Windows ISO is found in the
documented workspace or Downloads, and the intended VM directory is absent. P0-05 guest
acceptance and P1-07 remain open. Next: normal administrator-session provider check and
the owner's ISO path, then the documented new VM setup. No host feature/access change or
test rerun. See docs/windows-test-vm.md and IMPLEMENTATION.md.
Three resumed checks retain these blockers; continuous execution is blocked pending the
owner's provider/ISO/guest setup. No remaining acceptance checkbox is closed by the audit.

New4B read-only review candidate measured (2026-10-27): unchanged protocol2/24 inputs/
72 role calls complete. Baseline17/24, self-review20/24, specialist20/24; zero specialist
wins/regressions, so no strict benefit. Existing9B evidence is retained; no delegation or
default/routing change. P2-04 remains open. Next external release/isolation prerequisite
is the requested Hyper-V/Windows ISO/guest setup. Evidence:
.runtime/p2-04-4b-review/validation.json and IMPLEMENTATION.md.

Second completion candidate evaluated (2026-10-27): approved4B download and three real
capability/GPU checks pass. All60 first model executions are observed:53 passed,5 failed,
2 blocked; eight safety cases pass with no unauthorized effects. Eight original preflight-
only slots were completed after a bounded stable-snapshot guard fix; no executed outcome
was retried/replaced and the original report remains. Candidate is not qualified for routes;
9B stays the default. Native throughput110.22 tokens/s is not a paired9B latency comparison.
Evidence: .runtime/p2-05-candidate-4b/validation.json and IMPLEMENTATION.md.

Clean-install/upgrade preparation (2026-10-27): owner requests a separate VM and approves
qwen3.5:4b acquisition/evaluation. Hyper-V setup instructions are in docs/windows-test-vm.md;
host feature enablement/ISO/guest setup remain owner prerequisites. Built a separate
packaging-only0.1.1 NSIS upgrade fixture and retained the original0.1.0 installer. Original
inputs/artifacts are unchanged; seven fixture Rust checks pass, no ignored tests. No fixture
installer was executed and P0-05 third stays open. Evidence:
.runtime/p0-05-install-upgrade-fixture/build-result.json and IMPLEMENTATION.md.

Native screenshot capture/preview verified (2026-10-27): owner confirms the preview appears
in installed Studio. Consistent read-only installed metadata contains two new valid JPEG
captures,1600x900,141558/136112 bytes, with matching stored sizes and hashes. They are
unbound attachments; no model-image submission/recognition is inferred. Raw images are not
exported; temporary database copy removed. Capture/preview subcheck closes; P0-05 third
remains open for tested clean installation/upgrade/history/uninstall. Evidence:
.runtime/p0-05-native-capture-acceptance/validation.json and IMPLEMENTATION.md.

Native independent-Ollama preservation verified (2026-10-27): owner completes CONNECTED/X/
CLOSED in the installed application. Saved report confirms the same independent fixture
PID/creation time, listener and health survive native normal close, with captured native
descendants exited before fixture cleanup. Tested operator source and installed hashes
match; fresh inspection finds no remaining Studio/backend/Ollama images or service listeners
after harness cleanup. This third-increment subcheck closes; capture/preview and tested
clean-install/upgrade/history/uninstall remain open. Evidence:
.runtime/p0-05-native-shared-model-acceptance/validation.json and IMPLEMENTATION.md.

Native shared-model checker correction (2026-10-27): owner startup failure exposed a
listener-before-health race. Reproduced with real owned Ollama, then fixed bounded readiness
waiting for that same fixture without restarting shared services.62 relevant tests pass,
zero skips; Ruff and actual owned startup/cleanup pass. No Studio rebuild needed. Native
normal-close preservation remains unverified; rerun the documented operator exercise.
Evidence: .runtime/p0-05-shared-model-startup/validation.json and IMPLEMENTATION.md.

Native independent-Ollama acceptance support (2026-10-27): added an operator-only check
that uses an existing service or a separately owned fixture, verifies installed hashes,
requires native connection/normal-close observations, and checks unchanged service identity,
listener and bounded health before fixture cleanup.17 new contracts plus60 combined checks
pass with zero skips; Ruff passes. Actual exercise safely refuses the open owner Studio.
This is test support, not native acceptance. Capture remains pending (no new image in the
read-only installed snapshot). P0-05 third stays open. See docs/native-shared-model-check.md
and IMPLEMENTATION.md.

Baseline: 2026-10-22 audit. This is a proposed development checklist; unchecked items are
not claims of implementation. [Architecture findings R1–R10](ARCHITECTURE_REVIEW.md) and
[feature contracts F01–F12](FEATURE_GAP_ANALYSIS.md) provide rationale, current code,
integration points, dependencies, and security implications.

Native Markdown export (2026-10-27): owner clicked Export; the actual Downloads file is
independently read back and exactly matches the official two-message export,208 UTF-8
bytes/hash, with attachment body excluded. Export/download subcheck closes; no Save As
dialog is claimed from the notification. Capture/preview, native shared-Ollama preservation
and tested installation/upgrade/data behavior remain open. Evidence:
.runtime/p0-05-native-export-acceptance/validation.json and IMPLEMENTATION.md.

Native file-picker/text attachment (2026-10-27): owner explicitly confirms the paperclip
opened the Windows chooser successfully. Persisted87-byte fixture text/hash, user-message
binding and actual matching Chat response (one model call/25 generated tokens) independently
corroborate the flow. The narrow third-increment subcheck closes; capture/preview, native
export, shared-Ollama preservation and install/upgrade/data acceptance remain open. Evidence:
.runtime/p0-05-native-attachment-acceptance/validation.json and IMPLEMENTATION.md.

Native lifecycle acceptance (2026-10-27): owner completed the installed retry/fallback
exercise. Saved report and fresh process/listener inspection verify automatic1/2/4-second
backoff, exhausted retry budget, manual connection, owned normal-close cleanup and independent
Python preservation. Combined with earlier focus, interruption/no-replay, fresh approval
and component/frozen fault evidence, P0-05 first closes. Third remains open for physical
dialogs/capture/export, shared-Ollama preservation and clean-install/upgrade/data behavior.
Candidate download/VM prerequisites and failed benefit gates remain separate. Evidence:
.runtime/p0-05-native-lifecycle-acceptance/validation.json and IMPLEMENTATION.md.

Native retry/fallback prerequisite (2026-10-27): operator check now implements exclusive
loopback collision, actual installed process timing, manual restart confirmation and owned
close/Python-fixture preservation.12 new tests and43 combined checks pass with zero skips;
rendered recovery1/1 passes, Ruff passes. Installed hashes match; actual exercise refuses
the still-open owner instance without touching it. Native acceptance remains unverified.
Next: close Studio and run the documented operator check from normal PowerShell. Evidence:
.runtime/p0-05-native-retry-harness/validation.json and docs/native-recovery-check.md.

Fresh approval after crash (2026-10-26): a distinct resubmitted Agent task requests a new
approval and records denial; the interrupted task remains unchanged and the file stays
absent. Two real model calls/59 generated tokens verify post-crash execution. Pre-request
history identities are retained. This completes this pending-approval/no-replay/fresh-review
scenario; native retry exhaustion/manual restart is next. Full first/third stay open.
Evidence: .runtime/p0-05-native-recovery-fresh-denial/ and IMPLEMENTATION.md.

Pending-approval crash (2026-10-26): the captured waiting task becomes interrupted; the
unapproved file remains absent, old worker/backend/model processes exit, and the same
native instance owns fresh services. Zero approval resolutions/verifications/new task or
operation records follow the crash. Unfinished write stays conservatively unknown.
The scenario's interruption/no-replay subcheck closes; fresh approval on resubmission is
subsequently checked above. Native retry timing/fallback and full first/third stay open. Evidence:
.runtime/p0-05-native-pending-crash/validation.json and IMPLEMENTATION.md.

Idle backend-crash recovery (2026-10-26): owner reports automatic reconnection; unchanged
native PID now owns a fresh backend/model pair, old children have exited, and one listener
per service remains. Pre-crash record identities persist with zero new tasks/operations.
This closes the idle recovery subcheck only; pending-approval interruption is subsequently
checked above. Native retry-budget/fallback timing remains unverified. Evidence:
.runtime/p0-05-native-idle-crash-recovery/ and IMPLEMENTATION.md.

Normal reopen (2026-10-26): new native/backend/owned-Ollama chain and a completed Chat
generation are verified after owner reopens Studio. All pre-close conversation/task/message/
verification identity sets remain; older-transcript rendering is not explicitly confirmed.
The model's reset wording is not evidence of a reset; exact RESTART-OK compliance did not
pass. Subsequent idle backend-crash recovery is checked above. Full first/third
remain open. Evidence: .runtime/p0-05-native-reopen/ and IMPLEMENTATION.md.

Normal native close (2026-10-26): owner closed Studio; all four recorded native/backend/
owned-model PIDs have exited and ports17861/11434 are free. No observer termination or
service restart occurred. The idle-close subcheck passes; duration and unrelated-process
preservation were not established in this run. Full recovery/upgrade acceptance stays open.
Subsequent reopen/model startup and persisted record retention are checked above. Evidence:
.runtime/p0-05-native-normal-shutdown/ and IMPLEMENTATION.md.

Native second-launch evidence (2026-10-26): owner observes existing-window focus; a fresh
snapshot finds the original native/backend/Ollama PIDs and one backend listener, with no
persistent duplicate. This is a post-launch snapshot, not a continuous process trace.
The narrow subcheck closes; full native recovery/shutdown/upgrade acceptance stays open.
Normal close was subsequently checked above; reopening/history verification is next.
See .runtime/p0-05-native-second-instance/ and IMPLEMENTATION.md.

Latest native acceptance (2026-10-26): owner completed Agent deny/resubmit/approve.
Independent installed-state inspection corroborates false/true approval answers on distinct
tasks, denied/observed journal outcomes, zero/one artifact records and exact18-byte file
readback/hash. The specific approval subcheck closes; full P0-05 first/third stay open.
Second-instance focus was subsequently corroborated above; recovery/shutdown/upgrade remain separate.
Candidate download approval and configured VM prerequisites are still pending; failed
specialist/optimization gates remain rejected. See IMPLEMENTATION.md and
.runtime/p0-05-native-approval-verified/installed-observation.json.

## Audit deliverables completed

- [x] Read AGENTS.md, IMPLEMENTATION.md, application/test source, scripts and configuration.
- [x] Compare claims with source, available artifacts, and fresh regression/live/build checks.
- [x] Separate missing features, partial implementations, validation gaps, and external failures.
- [x] Create architecture review, feature assessment, priorities and measurable gates.
- [x] Leave application functionality and configuration unchanged.

Native progress/metadata correction(2026-10-26): owner confirms visible replies, Copy and
Stop in installed Studio. Found the installed EXE's3-byte Tauri NSIS bundle-tag difference
from the restored build copy. Manifest now preserves raw hashes and separately predicts
the unsigned default NSIS payload; ambiguous/signed/unknown inputs remain unavailable,
partial bundles omit predictions.9 release/discovery tests pass, Ruff passes, and the
prediction matches the actual installed EXE. Installer/application bytes unchanged; no
full native/upgrade checkbox closes. See .runtime/p0-05-nsis-payload-manifest/validation.json.

Installed recovery verified(2026-10-26): owner applied the corrected package/config. Actual
installed code matches all62 frozen source modules, settings match the exact backup plus
runtime paths, and the process tree verifies Studio-owned Ollama. Installed state records
a reported chat/330 generated tokens; both models are visible/GPU-resident. Fresh real
browser/screenshot1/1 and memory restart/change/reimport/forget1/1 pass against the installed
executable in disposable workspaces. Full native window/control/recovery/upgrade acceptance
remains unverified (UIA0 accessible windows here); P0-05 first/third remain unchecked.
See .runtime/p0-05-installed-ollama-recovery/validation.json and IMPLEMENTATION.md.

Installed-runtime correction(2026-10-26): owner reports Ollama missing in installed Studio;
actual portable executable/models live outside its config base/PATH. Trusted runtime paths,
standard Windows discovery and an operator configuration helper now address that mismatch.
850 default tests775 passed/75 skipped;32 focused and7 new frozen startup/runtime/coding/
MCP checks pass. Updated NSIS build succeeds. Real owned service starts, but managed model-
store read is access-denied; inference/native application verification is still pending in
the normal session. Install the update and run configure-installed-ollama.ps1 with Studio
closed. See .runtime/p0-05-ollama-location-fix/validation.json. No new acceptance box closes.

Owner-session recovery(2026-10-26): setup/dev/build were reported run, and the actual
NSIS installer now exists with bundle_succeeded=true. Independently verified all115 build
inputs, all3 artifact hashes,61 source-equal frozen modules and matching deployed sidecar/
resource copies. New frozen runtime/socket/real-model browser/coding checks17/17 pass;
frozen MCP1/1 and Rust7/7 pass, no skips. Lock/npm consistency passes; locks retained.
P0-05 second increment closes at build/frozen-package scope. Native UI/single-instance/
recovery, standard-user install and upgrade remain unverified; first/third stay open.
The historical managed10013 failure no longer blocks this produced installer. Evidence:
.runtime/p0-05-owner-installer-verification/validation.json and dist/release-manifest.json.

Blocked audit3(2026-10-26): safe memory/release increments are complete; unchecked items
still lack prerequisites. With Studio/Vite absent at preflight, a fresh owned native run
actually launches but fails WebView2 GPU0xc0000022/unusable GPU, no frontend request, with
owned cleanup verified. The pinned NSIS endpoint again fails10013. No second completion
candidate or configured VM appeared. Failed specialist/performance gates remain rejected,
and optional OCR/document work has no selected input need. No unchecked box is closed.
Continuous execution is blocked, not complete, after the third consecutive prerequisite
audit; resume after owner-session native evidence/permitted installer access or another
approved independent prerequisite changes. Evidence: IMPLEMENTATION.md and
.runtime/roadmap-gates/after-memory-blocked-audit-3/final-gates.json.

Latest release progress(2026-10-26): current qualified memory UI/backend builds as an
optimized release candidate with offline Cargo and the documented runner overlay. Deployed
sidecar smoke checks6/6 pass,0 skipped; ZIP integrity/member hashes match. This is not an
installer or native-window acceptance. Fresh pinned NSIS3.13 acquisition fails10013; a
read-only UIA probe sees zero accessible native windows here. Existing Studio/Vite remain
external test prerequisites. P0-05 stays unchecked. Evidence/candidate:
.runtime/roadmap-gates/after-memory-20261026/release-validation.json.

Post-memory prerequisite recheck(2026-10-26): native preflight refuses to disturb existing
Studio (native not launched; not verified), and Vite owns1420. No new GPU result. NSIS is
undiscovered in checked PATH/cache/Program Files locations; acquisition was not retried.
No configured/discovered VM provider, and only one installed model advertises completion;
the new embedding model is not a second routing candidate. Preserve existing processes.
Next: owner-session P0-05 native acceptance after closing Studio/Vite; installer acquisition/
build and standard-user install remain separate. See IMPLEMENTATION.md and
.runtime/p1-03-memory-acceptance/remaining-gates.json. Historical failed candidate gates stay open.

Current evidence (P1-03 B3 combined qualification,2026-10-26): actual production file
retrieval after restart passes the fixed64-question comparison: literal hybrid32/32 versus
lexical32/32; paraphrase hybrid30/32 versus lexical14/32; zero cross-project results.
Actual chat citation/provenance, changed-source history/vector exclusion, whole-source
forget and source-chat cascade pass in the same run,43.984s.89 focused tests83 passed/
6 opt-in skips; Ruff passes. B2a/B2b source/frozen/rendered artifacts remain unchanged.
B3 and P1-03 B close at this bounded text-memory scope; Zephyr/Acorn misses remain.
Native/installer, VM isolation and other candidate-model gates stay open. Evidence:
.runtime/p1-03-memory-acceptance/validation.json.

Previous evidence (P1-03 B2b source controls,2026-10-26): file review/import, stale checks,
conflict refusal, fresh reimport/whole-source forgetting, blank-conversation creation and
late preview/metadata guards pass against source/frozen backends.3 frozen UI scenarios
pass,4 source legacy/blank UI checks pass;76 focused tests,72 passed/4 skipped;23 frontend
tests, Ruff and TS/Vite runner build pass. Python/backend artifacts are unchanged from
B2a below. B2b closes; combined B3 qualification is next. Native/installer gates remain
open. Evidence: .runtime/p1-03-memory-source-ui/validation.json.

Previous evidence (P1-03 B2a file-source backend,2026-10-26):836 default tests,
765 passed/71 skipped,340.462s;222 focused,219 passed/3 skipped;23 frontend tests,
Ruff/lock and TS/Vite pass. Actual source/frozen file import, restart recall/citation,
changed-source invalidation, reimport/forget pass. Rendered file provenance/forgetting,
semantic/backup and frozen coding pass; rendered restore is blocked by the existing Vite
listener on1420, left untouched. Populated backup/restore storage tests pass. Source-equal
73-module wheel/61-module frozen backend pass. B2a alone closes; B2b selection/review
and combined B3 remain open. See .runtime/p1-03-memory-sources/validation.json.

Previous evidence (P1-03 B1b optional hybrid context,2026-10-26):808 default tests,
739 passed/69 skipped,334.923s;159 focused,155 passed/4 skipped;23 frontend tests and
TS/Vite pass. Source/frozen actual-model recall, restart, citation, forget/stale admission
and rendered source/frozen index/stop/scope workflows pass. Ruff/lock and source-equal
72-module wheel/60-module frozen backend pass. File sources/chunks B2 and combined B3
remain open, as do native installer gates. See docs/project-memory.md and
.runtime/p1-03-memory-integration/validation.json.

Previous evidence (P1-03 B1a explicit note index,2026-10-26):790-case regression
passes,723 passed/67 skipped,349.059s;164 focused,161 passed/3 skipped. A separately
added SQL-publication fault test passes. Actual source embedding/index contracts2 pass;
actual frozen API/restart/forget and existing frozen coding each pass. Ruff/lock,71-module
wheel and59 source-equal frozen modules pass. Index/search is explicit authenticated API
only; B1b prompt/UI and B2/B3 remain open. See docs/project-memory.md and
.runtime/p1-03-note-index/validation.json.

Previous evidence (P1-03 B0 embedding prerequisite,2026-10-26):773 default tests,
707 passed/66 skipped,330.917s. The first fixed actual study passes:32/32 literal,
30/32 paraphrase hybrid versus14/32 lexical, zero cross-project results. Local vector
contract, bounded transport/failure tests, Ruff/lock and source-equal69-module wheel pass.
Semantic Studio integration remains B1a/B1b/B2/B3. See docs/project-memory.md and
.runtime/p1-03-embedding-evaluation/validation.json. The owner native preflight now
requests the frontend without observed GPU failures; native application gates remain open.

Previous evidence (P0-05 native diagnostic prerequisite,2026-10-26):757 default tests,
692 passed/65 skipped,327.244s;13 focused checks including the actual owned native
diagnostic pass. The diagnostic reports observed_failure, GPU subprocess0xc0000022,
GPU unusable and owned cleanup. This is diagnostic acceptance, not working native UI.
Ruff, lock consistency and source-equal67-module wheel/import pass. Native first/full
installer gates remain unchecked. See docs/native-diagnostics.md and
.runtime/p0-05-native-diagnostics/validation.json.

Previous evidence (P2-02 read-only MCP provider,2026-10-26):744 default tests,
680 passed/64 skipped,318.045s; focused MCP15 passed/2 opt-in skips; actual local-model
MCP workflow, actual frozen stdio server and frozen approved-test regression also pass.
Pinned SDK2.3.0, immutable namespaced adapter, real handshake/list/call, schema-review
failure, scope/output limits and owned-process cancellation are verified. Locked offline
sync, Ruff and source-equal wheel pass. No general external-server/HTTP support or OS
isolation is claimed. Evidence: .runtime/p2-02-mcp-integration/; docs/mcp.md.

Previous evidence (P3-02 A1b1 actual paired trial,2026-10-26): all120 actual model
attempts and16 safety attempts complete. Both profiles56/60 model,8/8 safety, no observed
unauthorized effects. Worker p50/p95: fixed2K13.578/17.766s, configured8K7.078/11.750s;
generation stays near73 token/s and sampled model VRAM matches. All60 pairs improve,
but a candidate download case loses one repetition, failing predeclared per-case
nonregression. No default is applied. A1b1 measurement closes; cold/adoption and full
P3-02 remain open. Unchanged sources reuse A1a regression/package gates below.
Evidence: .runtime/p3-02-live-20261026/validation.json; docs/probe-qualification.md.

Previous evidence (P3-02 A1a matched comparison harness,2026-10-25):727 default tests,
665 passed/62 skipped,303.792s; targeted90 passed/3 skipped,27.063s;17 timing-focused
tests pass. The separate136-workflow protocol matrix passes in126.491s, using simulated
inference and real tools. Ruff and offline wheel/source/import checks pass; retained
matrix evidence revalidates. A1a closes as development infrastructure only. A1b/overall
P3-02 stay open: no actual-model broad/cold result or default applied. Current model
endpoint remains unavailable; MCP offline/online dry-runs fail1/2, online socket10013.
Evidence: .runtime/p3-02-qualification/validation.json; docs/probe-qualification.md.

Previous evidence (P3-02 A0 warm probe-context feasibility,2026-10-25): all12 actual
samples/six alternating pairs pass the counter microtask, actual context/VRAM receipts
and invariant payload checks. Matching8K probe versus existing2K reduces observed fresh
worker-without-warm-setup p50 from8.218s to1.047s; native loading7.091s to0.007s.
Default715 tests:654 passed/61 skipped; targeted49 passed/one skipped, Ruff and offline
wheel/source/import checks pass. No production default/service/config change. A0 only
closes; matched broad quality/safety and controlled cold conditions remain before adoption.
Evidence: .runtime/p3-02-probe-context/validation.json; docs/probe-context-trial.md.

Previous evidence (P2-04 A0 review trial,2026-10-25): eight fixtures/three repetitions,
24 complete inputs/72 ordinary model calls per protocol, with balanced second-pass order.
Protocol1 scores6/24 first pass,9/24 self-review,6/24 specialist. Grounded protocol2
scores18/24,21/24,19/24 respectively: zero specialist wins over equal-budget self-review,
two regressions. No delegation is activated. Both complete runs and unchanged oracle remain.
Pre-final-guard default709 tests:648 passed/61 skipped,301.316s. Final focused70:69 passed/
one legacy live opt-in skip; Ruff and offline wheel/source/import checks pass. A final
source-snapshot guard changes rejection behavior only; retained observations revalidate
against current source checks. A0 closes as an evaluator, not P2-04 integration. Next:
P3-02 may investigate the observed model-load overhead without restarting the user's service.

Previous evidence (P1-06 B2b message/export acceptance recovery,2026-10-25): both actual-model
chat/slash UI scenarios pass without skips (62.526s).20 history,3 discovery,3 affected source
UI and3 affected packaged UI checks pass without skips; Ruff passes. The browser-preview
test now owns an ephemeral fixture origin and asserts actual returned URL/title/text,
instead of relying on a shared Vite route. No production code, assets or binary changed;
the P2-03 B1 default/build/package results below remain the verified product boundary.
The earlier model failures and new adjacent-test timeout are retained. B2b/B2/B close at
source/browser UI scope; installed native acceptance remains separate. Evidence:
.runtime/p1-06-messages-recovered/validation.json. Next: reassess P1-03 B model acquisition
and remaining native/dependency gates before P2-04 specialist work.

Previous evidence (P2-03 B1 directory inspections,2026-10-25): **699 default tests /638 passed /
61 skipped**,301.966s;172 targeted and56 final packaged checks pass without skips.
TS/Vite/23 Node/Ruff pass;33 archived code entries equal source. Persisted baseline,
debounce, trigger admission, disable/stop/restore and real file/runtime/UI paths pass.
The full regression exposed a late-addition observation gap; bounded filename revalidation
and a timestamp-restored reproduction now pass. Both failed runs remain recorded.
B0/B1/B close at Studio-only read-only workflow scope. Real-model quality, native install
and OS isolation gates remain separate. Next: assess P2-04's restricted review/evaluation
dependencies. See docs/directory-inspections.md and
.runtime/p2-03-directory-workflow/validation.json.

Previous evidence (P2-03 B0 directory observations,2026-10-25): **671 default tests /611 passed /
60 skipped**,270.338s;54 targeted tests:53 passed/one legacy symlink-creation skip.
All14 new snapshot cases pass without skips, including actual Windows junction/hardlink
and concurrent replacement checks. Ruff passes.59 activated runtime/frontend source files,
assets and executable match A1, whose52 packaged gates are reused. B0 closes as a private
source-only helper; no directory trigger is activated. Next: B1 durable debounce/dispatch
and actual UI/runtime integration. Evidence: .runtime/p2-03-directory-snapshot/validation.json.

Previous evidence (P2-03 A1 interval inspections,2026-10-25): **657 default tests /597 passed /
60 skipped**,285.348s;131 targeted and52 final packaged checks pass without skips.
TS/Vite/23 Node/Ruff pass;30 archived code entries equal source. Runtime-only read-only
intervals, explicit UTC/misfire/timezone policies, disable and persisted emergency pause
are verified. The packaged history loading regression also passes. A/A1 close; directory
triggers (B), actual-model/native and other open gates remain. See
.runtime/p2-03-interval/validation.json and docs/interval-inspections.md.

Previous evidence (P2-03 A0 queue admission,2026-10-25): **633 default tests /574 passed /
59 skipped**,252.510s;97 targeted and48 packaged regression checks pass without skips.
Ruff passes;27 archived code entries match source. Unchanged frontend source/assets match
the P2-01 TS/Vite/19 Node boundary. A0 closes for private durable admission primitives;
no scheduler/automatic dispatch exists yet. Next: P2-03 A1 interval workflow integration.
Evidence: .runtime/p2-03-queue/validation.json. Model/native gates remain open.

Previous evidence (P2-01 read-only checkpoints,2026-10-25): **620 default tests /561 passed /
59 skipped**,248.331s; all48 final packaged checks pass without skips.130 targeted checks,
late32 image/continuation regressions, source crash/restart2 and rendered1 pass. TS/Vite/
19 Node/Ruff pass;26 archived code entries match source. P2-01 closes for selected-file
read-only inspections only; ordinary agent tasks stay non-resumable. Next: P2-02 SDK/
stdio-provider compatibility and dependency acquisition. Model/native gates remain open.

Previous evidence (P1-06 B4 manual retention,2026-10-25): **598 default tests /540 passed /
58 skipped**,232.144s; all90 targeted and45 packaged UI/HTTP/runtime checks pass without
skips. Strict TS/Vite/19 Node/Ruff pass;25 archived code entries match source. Bounded exact
previews, explicit confirmation, atomic cascades, memory provenance and selected/active
work preservation are verified. B4 closes; B2b/B2/B, actual-model UI and native installed
product gates remain open. Next independent increment: P2-01 read-only checkpoint.

Previous evidence (P1-06 B3b2 restore activation,2026-10-24): **584 default tests /527 passed /
57 skipped**,215.135s; all79 targeted, late restored-worker1 and43 packaged UI/HTTP checks
pass without skips. TS/Vite/19 Node/Ruff pass;24 archived runtime entries match source.
Confirmed restore/rollback, fresh rollback capture, state ownership, crash boundaries and
900px stale-response/cursor recovery are verified. B3b2/B3b/B3 close; B4 retention is next.
Message/export actual-model UI and native installed-product gates remain open.

Previous evidence (P1-06 B3b1 restore preparation,2026-10-24): **559 default tests /503 passed /
56 skipped**,214.716s; all54 targeted and18 packaged HTTP/runtime/socket/loop checks pass
without skips. Ruff passes;21 archived code entries match source. Frontend source/assets
match B3a's passing build/19 Node gates. Only preparation closes; B3b2 activation/restart/
rollback UX is next. B3b/B3 and separate model/native gates remain open. See IMPLEMENTATION.md.

Previous evidence (P1-06 B3a consistent backup,2026-10-24): **544 default tests /488 passed /
56 skipped**,207.617s; final39 source targeted, source UI1 and all39 packaged checks pass
without skips. TS/Vite/19 Node/Ruff pass;20 archived sidecar entries match source.
Confirmed private snapshots are verified; B3a alone closes. Staged restore B3b is next;
B3, retention and the separate actual-model/native gates remain open. See IMPLEMENTATION.md.

Previous evidence (P1-06 B2b Task-history component,2026-10-24): **532 default tests /
477 passed /55 skipped**,201.128s; all38 packaged UI/runtime/socket/loop checks pass,
167.695s, and final3 affected rendered checks pass,31.885s. Source44 passed/3 skipped,
TS/Vite/19 Node/Ruff pass;19 archived sidecar entries match source. Task-history child
is complete; message/export actual-model gate and B2b/B2/B remain open. Next independent
work: B3 online backup/validated restore. See IMPLEMENTATION.md for evidence and limits.

Previous evidence (P1-06 B2b conversation sidebar component, 2026-10-24): **522 default
tests /469 passed /53 skipped**,206.116s; all36 frozen UI/runtime/socket/loop checks pass
without skips,148.098s. Source history12 and real72-conversation rendered scenario pass;
strict TS/Vite,18 Node checks and Ruff pass. All18 inspected sidecar code entries match
source. Fifty-row sidebar/search, older-page controls, stale-response rejection, selected
metadata, rename/delete/new/reload are verified without automatic full-list GETs. Only
the conversation component closes; B2b message/task paging/export and B2/B remain open.

Previous evidence (P1-06 B2a bounded history API, 2026-10-24): **520 default tests /
468 passed / 52 skipped**, 206.244s; all30 source history/migration/socket and35 frozen
UI/runtime/socket/loop checks passed without skips. Ruff passed; unchanged frontend
hashes match B1's passing build/18 Node gates. Rebuilt sidecar18 code entries match source.
Authenticated bounded keyset pages/index-only migration4 are verified; legacy endpoints,
model context and desktop controls are unchanged. B2a alone is complete. Next B2b desktop
paging; B2, B3/B4 and model/native gates stay open. See IMPLEMENTATION.md.

Previous evidence (P1-06 B1 keyboard/dialog/activity access, 2026-10-24): **508 default
tests / 456 passed / 52 skipped**, 203.046s; all **34 frozen UI/runtime/socket/loop checks**
passed without skips, 133.150s. Eighteen Node checks, strict TS/Vite, Ruff and a final
rendered keyboard/visual scenario passed. Native dialogs plus explicit Tab cycling keep
focus contained; safe Escape/return, stacked approvals, emergency stop and 900px activity
access are verified. B1 alone is complete; B2 paging is next, with B3 backup/restore and
B4 retention open. Actual model/native install gates remain open. Evidence: IMPLEMENTATION.md.

Previous evidence (P1-06 A UI separation/scoping, 2026-10-24): **507 default tests /
456 passed / 51 skipped**, 201.697s; all **33 frozen UI/runtime/socket/loop checks** passed
without skips, 129.079s, and 16 source transport checks passed. Strict TS/Vite, 18 Node
checks and Ruff passed. Sixteen PYZ modules plus the runtime entry match the rebuilt
sidecar source. Conversation/task activity, transient owned previews and globally identified
approvals are verified; Windows ASGI uses a server-only Selector loop after the retained
Proactor reset failure. Worker policy/security boundaries are unchanged. P1-06 A is
complete; B remains open. Native install and current P1-03 model-access gates remain open.

Previous evidence (P1-03 A explicit memory, 2026-10-24): implemented with **503 default
tests / 453 passed / 50 skipped**, 188.568s; 32/32 lexical and bounded-context recall with
64 same-project distractors and zero foreign IDs. All 28 frozen UI/runtime/socket checks
passed; both final memory UI flows, TypeScript/Vite, 11 Node checks and Ruff passed.
Sixteen frozen modules match source. Earlier actual Qwen restart recall passed, but a
fresh owned Ollama startup lists no models and logs manifest `Access is denied`; the
current real-model gate is blocked and A stays unchecked. No security controls changed.
P1-03 B shares the model dependency; continue independently with P1-06 A. See
IMPLEMENTATION.md and docs/project-memory.md for evidence and recovery steps.

Previous evidence (P1-05 B context budget/compaction, 2026-10-23; finalized after access
recovery): **486 default tests, 439 passed / 47 skipped**, 188.381s. Four final actual-model
tests passed, 57.765s, including native overflow rejection, all six semantic pairs, real
Studio history compaction/artifact and independently verified autonomous counter repair.
Two original-image regressions and two source UI cases passed. Final frozen build and
24 UI/runtime/socket checks, TS/Vite, eleven Node tests and Ruff passed. Fifteen frozen
modules match current source. P1-05 B is complete at its bounded estimate/excerpt scope;
next actionable increment is P1-03 A. Exact tokenization, long-term memory, native install
and the earlier model corpus failures remain separate limitations.

Previous evidence (P1-05 A inference options/admission, 2026-10-23; finalized after access
recovery): **463 default tests, 421 passed / 42 skipped**, 181.189s. Five current-source
real Ollama checks passed without skips, 27.867s; final frozen build and all 22 rendered
UI/runtime/WebSocket checks passed, 85.825s. TypeScript/Vite, eleven Node checks and Ruff
passed. Unified max-output/thinking/residency settings, capability admission/cache,
incomplete-response handling and native/first-token timings are verified. P1-05 A is
complete; next actionable increment is P1-05 B. No token-reserve/compaction or native
installer claim; the earlier model baseline failures remain unchanged.

Previous evidence (P1-04 journal/recovery, 2026-10-23): **439 default tests, 399 passed /
40 skipped**, 164.317s; targeted 71 passed / 1 skipped, 39.864s. Final actual Qwen Studio
write/read workflow: 1 passed / 0 skipped, 7.368s. Both source rendered journal scenarios
passed; final frozen build and 11 frozen UI/WebSocket checks passed, 34.618s. Ruff,
TypeScript/Vite and 11 Node checks passed. Unknown effects are not replayed or certified
by matching files. P1-04's Studio observation/reconciliation increment is complete;
next actionable increment is P1-05 A. Native/install and OS-isolation gates remain.

Previous evidence (P1-02 counted acceptance, 2026-10-23): **407 default tests, 370 passed /
37 skipped**, 149.320s; 28 targeted passed / 1 skipped, 21.455s; Ruff passed. Actual-model
counter opt-in: 1 passed / 0 skipped, 23.628s; structured initial 3 tests/1 failure, then
8 passed, independently counted 8 passed and separate 6-test oracle, with seed integrity
and diff review. Four approval/count-evidence regressions added. P1-02 A/B complete at
their stated contracts. Next actionable increment is P1-04; native/install gates remain.

Previous evidence (P1-08 B execution/live acceptance, 2026-10-23): default **403 tests,
366 passed / 37 skipped**, 150.708s; final targeted **41 passed / 2 skipped**, 5.900s;
Ruff/wheel/load checks pass. Protocol matrix: 60/60 workflows plus 8/8 real safety cases.
Actual `qwen3.5:9b` corpus: **55/60 (91.7%)**, 8/8 safety, zero observed critical effects,
complete native metrics; 67.38 tokens/s, p50 7.328s / p95 12.328s. Five real-model checks
also pass; skipped defaults stay explicit. Five corpus failures are preserved. The legacy
counter fixture's configured-count verdict remains inconclusive, so next is canonical
profile acceptance before P1-02's broad gate/P1-04. See docs/agent-evaluation-baseline.md.

Previous evidence (P1-08 B corpus contract, 2026-10-23): **383 unique default tests,
347 passed / 36 skipped**, 144.823s; Ruff passed. Twenty new tests all pass with the
local-browser denial enabled (1.912s); the default skips that case. Seven other denials
exercise actual Tools. A wheel contains the matching corpus and loads from an isolated
unpacked path. Twenty model task definitions, eight separate safety cases, independent
read-only oracles and strict sixty-repeat/eight-safety report contracts are verified.
This is not a workflow runner or measured model score. Next: B's bounded execution
adapter; actual repeated quality remains gated by local-model access (fresh tags timeout).

Previous evidence (P1-08 A observability, 2026-10-23): **363 unique default tests,
328 passed / 35 skipped**, 142.349s; Ruff passed. Seventeen new diagnostic cases and
all 70 targeted checks pass; nine rendered scenarios and thirteen rebuilt frozen-backend/
UI/runtime checks pass. TS/Vite and eleven Node checks pass. Existing 22 schemas and
inference payload code are unchanged. Studio run/decision/tool IDs, bounded taxonomy/
timing and content-free export are verified; no corpus score, checkpoint/CLI trace or
native-install claim. Next: P1-08 B corpus/runner, keeping model quality gated until an
actual service is available. Continuous execution remains active.

Previous evidence (P1-02 background output/readiness, 2026-10-23): **345 unique default
tests, 311 passed / 34 skipped**, 134.371s; Ruff passed. Twenty new background cases and
all 58 targeted checks pass; eight rendered scenarios and twelve rebuilt frozen-backend/
UI/runtime checks pass. TS/Vite and eleven Node checks pass. Existing 21 schemas are
unchanged; command_status is the twenty-second tool. Initial P1-02 implementation components
are present; broad A/B checkboxes remain open for current real-model acceptance. A fresh
tags probe has no listener (10061); native/install gates stay open. Next safe independent
increment: P1-08 A observability, whose explicit verifier dependencies are satisfied.
Continuous execution remains active.

Previous evidence (P1-02 foreground command streaming, 2026-10-23): **323 unique default
tests, 291 passed / 32 skipped**, 130.973s; Ruff passed. Fifteen new stream checks and
all 83 targeted checks pass; six rendered scenarios and ten rebuilt frozen-backend/UI/
runtime checks pass. TS/Vite and ten Node checks pass. All 21 tool schemas are unchanged.
Output is bounded/redacted before durable events, with honest interruption and replay.
B stays open for background output/readiness; current model/native/NSIS gates remain open.
Next: background readiness within P1-02 B. Continuous execution remains active.

Previous evidence (P1-02 reviewed patch sets, 2026-10-23): **306 unique default tests,
276 passed / 30 skipped**, 127.115s; Ruff passed. Seventeen new patch checks and all
91 targeted regressions pass; four rendered UI scenarios and eight rebuilt frozen-backend/
UI/runtime checks pass. TS/Vite and seven Node checks pass. Existing 20 schemas are
unchanged; apply_patch is the twenty-first tool. B remains open for bounded command
streaming and background readiness. Current model/native/NSIS gates remain open. Next:
bounded command streaming within P1-02 B. Continuous execution remains active.

Previous evidence (P1-02 scoped search, 2026-10-23): **288 unique default tests,
259 passed / 29 skipped**, 122.292s; Ruff passed. Seventeen search cases and fourteen
tool-contract cases pass. Three rendered UI scenarios and seven rebuilt frozen-backend/UI
checks pass; TypeScript/Vite and seven Node checks pass. Original 19 schemas are unchanged;
search_files is the twentieth tool. B remains open for reviewed patch sets, streamed
command output and readiness. Current model/native/NSIS gates remain blocked. Next safe
increment: reviewed patch sets within P1-02 B. Continuous execution remains active.

Previous evidence (P1-02 artifact verifier, 2026-10-23): **270 unique default tests,
242 passed / 28 skipped**, 121.129s; Ruff passed. Thirteen artifact checks plus eighteen
test-verifier checks pass; two rendered UI scenarios and three rebuilt frozen-backend/UI
checks pass. TypeScript/Vite and seven Node checks pass. Both initial verifier components
are implemented; full A stays open for current model-driven acceptance. Model availability,
native WebView and NSIS gates remain blocked. Next safe independent increment: scoped
repository search within P1-02 B. Continuous execution remains active.

Previous evidence (P1-02 first verifier, 2026-10-23): **256 unique default tests,
229 passed / 27 skipped**, 118.670s; Ruff passed. Eighteen verifier checks pass; real
rendered approval/test/evidence UI and five rebuilt frozen-backend checks pass. TypeScript,
Vite and seven Node tests pass. The configured-unittest verifier is complete at its scope;
P1-02 A remains open for artifact readback/hash and model-driven acceptance. Model access,
native WebView and NSIS blockers remain. Next: P1-02 A's artifact verifier.

Previous evidence (P1-01 contracts, 2026-10-23): **238 unique default tests,
211 passed / 27 skipped**, 111.417s; Ruff passed. Fourteen new targeted contracts pass;
four actual frontend/approved-test/local-browser checks pass (7.033s), with no inference
claimed for their metadata fixture. TypeScript/Vite and seven Node checks pass. All 19
model-facing schemas exactly match the saved baseline. P1-01's contract increment is
complete; current model-dependent regression is externally blocked by manifest access
denial in the managed Ollama launch. Native/NSIS gates remain open. Next: P1-02 A's
single configured-test verifier. Continuous execution remains active.

Previous evidence (P0-05 packaging, 2026-10-22): **223 unique default tests,
197 passed / 26 skipped**, 109.673s; Ruff passed. Seven Rust tests pass. Actual final
frozen-sidecar runtime/socket/coding/real-model browser acceptance: **15 passed**, 51.283s.
Sidecar and optimized release application build; artifact/source hashes verified.
NSIS download is blocked by Windows socket error 10013; no installer exists. Native
WebView gate stays open. Next safe independent increment: P1-01 (depends on completed
P0-03). P0-05 checkboxes remain open; continuous execution remains active.

Previous evidence (P0-05 lifecycle, 2026-10-22): **219 unique default tests,
195 passed / 24 skipped**, 105.661s; Ruff passed. Four Rust and seven Node tests pass;
TypeScript/Vite and an isolated Windows executable build pass. Actual Ollama/UI including
rendered recovery: six passed, 23.638s. Native second-instance acceptance failed before
readiness with WebView2 resource-in-use; P0-05 first stays unchecked. Next independent
increment: packaging/frozen-worker validation. Continuous execution remains active.

Previous evidence (P0-04 complete, 2026-10-22): **209 unique default tests,
186 passed / 23 skipped**, 101.199s; Ruff passed. Targeted image/lifecycle/startup:
**20 passed**, 6.594s. Actual Ollama/Edge image-context + spawned Studio preview:
**2 passed**, 13.261s. Skips remain unpassed in default discovery. P0-04 is complete;
next is P0-05 first increment: native diagnostics, owned lifecycle and bounded restart.
Continuous execution remains active. Native/installer gates remain incomplete.

Previous evidence (P0-03 second increment, 2026-10-22): **188 default tests,
167 passed / 21 skipped**, 100.179s; Ruff passed. Final targeted checks: **29 passed**,
13.020s; real local Playwright checks: **6 passed**, 8.366s; actual Ollama/UI/coding:
**6 passed**, 61.616s. Protected/unprotected Windows DACL retention and real junction
refusal pass. Both P0-03 increments are complete; continuous execution proceeds to
P0-04 first increment. Native/install acceptance and skipped checks remain unpassed.

Previous evidence (P0-03 first increment, 2026-10-22): **173 unique default tests,
155 passed / 18 skipped**, 85.624s; Ruff passed. Targeted file/Git/worker checks:
**20 passed**, 7.883s. Existing actual Ollama/UI checks: **5 passed**, 31.478s.
P0-03 review version checks are complete; atomic publication/downloads and Git helper
configuration remain its next increment. Continuous execution proceeds one increment at
a time; skipped/native/installer checks remain explicitly unverified.

Previous evidence (P0-02 third increment, 2026-10-22): default regression **163 unique tests,
145 passed / 18 skipped**, 79.192s; Ruff passed. Final replay/delivery/rendered-UI checks
**15 passed, no skips**, 25.531s, including all 5,001 events once through reconnect and
backend restart. All **five existing live Ollama/UI checks passed**, 32.478s. Six Node
state tests, TypeScript and the Vite production build pass. P0-02 is complete; P0-03's
first increment is next. Default skips remain unpassed in that run; the rendered replay
UI and existing live scenarios were separately enabled and passed. No native/install pass
is inferred. Prior real-model coding acceptance and user-run normal browser/Notepad
evidence remain attributed in IMPLEMENTATION.md. The P0-01 source/lock manifest remains
an immutable snapshot; subsequent changes and evidence are recorded separately.

## P0 — Critical fixes and verification

### P0-01 — Establish an accurate acceptance baseline

- [x] **First increment:** separate reusable test fixtures from discoverable test cases and
  produce a dated current-status table. Supersede stale README/IMPLEMENTATION claims while
  retaining historical results. Record lockfile versions and a reviewable source baseline;
  the current Git repository has no commits and all source is untracked.
  Verified 2026-10-22: 92 distinct discovered tests, preserved assertions/opt-ins, passing
  default/targeted/live-UI checks and lint; dated README/IMPLEMENTATION summary and lock/source
  manifest plus local snapshot. No Git commit or application functionality change.
- [x] **Acceptance increment:** run the existing interactive/public acceptance and add one real
  model-driven coding bug-fix acceptance in a disposable project. Keep public-network and
  physical-desktop checks explicit opt-ins, not mandatory on headless fixture runners.
  All independent acceptance gates below are satisfied, with user-run and assistant-run
  evidence attributed separately. This does not close unrelated roadmap items.

  - [x] Public browser acceptance: following the example.com assertion repair, the user
    reported `Ran 111 tests in 36.246s` / `OK (skipped=12)` for the requested normal-session
    browser validation. This enables all four browser tests, covering public TodoMVC
    extraction/app-route navigation/two tabs/unsubmitted draft, plus local full-page navigation,
    downloads and denied POST. Evidence is the user-provided summary in IMPLEMENTATION.md;
    no managed-session public pass or physical desktop/model pass is inferred.
  - [x] Physical Notepad acceptance: following `validate.ps1 -Desktop`, the user reported
    `Ran 111 tests in 48.994s` / `OK (skipped=15)`. The script enables the single physical
    Notepad launch/type/save/readback test; the one fewer skip agrees with that configuration.
    User-provided summary is recorded in IMPLEMENTATION.md. This does not establish wider
    UIA/menu/screenshot/native-app behavior or a managed-session desktop pass.
  - [x] Real model-driven coding bug-fix acceptance in a disposable Git repository:
    `tests.test_coding_acceptance.LiveCodingTests` passed against actual local Qwen3.5 9B.
    Agent observed test exit 1, fixed counter.py, generated five tests, reran eight passing
    tests and reviewed the final diff. Independent rerun passed eight tests; six private
    behavior checks passed. Six deterministic verifier/security tests and full regression
    pass; no model mock, user-project write, policy relaxation or production rewrite.
  - [x] Independent WebSocket negative/positive acceptance gate: nine real loopback backend
    tests pass, including wrong/missing credentials, malformed/binary frames, actual five-second
    authentication timeout, cursor limits, forbidden origins and a valid private snapshot.
    Fixed explicit close handling, non-ASCII credential rejection and cursor validation;
    full regression and Ruff pass. This gate is independent of model-driven coding acceptance.
- **Acceptance:** deterministic regressions pass with an explained unique test count;
  public demo/navigation/form check passes with zero external submissions; Notepad
  launch/type/save/readback passes in an unlocked session; real model creates/fixes counter
  code and runs at least one meaningful test. Each claim links command, environment,
  timestamp and evidence; an unavailable environment is reported as blocked, not passed.
- **Increment boundary:** the checked first increment covers discovery, evidence/status and
  source/dependency baselining. WebSocket, public browser, physical Notepad and real-model
  coding acceptance gates are complete. P0-01 is complete; this single-task check is not a
  general coding quality benchmark, OS isolation guarantee or installed Studio acceptance.
- **Tests:** existing `test_live`, `test_studio`, feature/slash/UI tests, plus autonomous
  disposable-repository success/failure oracles. `tests/test_studio_socket.py` now supplies
  explicit credential, timeout, malformed-frame, cursor and origin negative tests plus
  authenticated snapshot/disconnect positives. No production project mutation.
  `tests/test_coding_acceptance.py` adds six positive/negative verifier tests and one
  explicit opt-in real coding test, using the plain helper in `tests/coding_acceptance.py`.
- **Dependencies:** normal Windows session supplied browser/desktop evidence; an existing
  normally launched local Ollama service supplied inference. No model-store ACL changes.
  **Contracts:** F04, F11; validation work before framework changes.

### P0-02 — Make task failure and event recovery deterministic

- [x] **First increment:** compensate `proc.start`, Job Object, initial pipe-send, and
  monitor-start failures; close owned resources and persist a terminal failure.
  Verified 2026-10-22: ten startup/API fault tests pass, including real gated processes,
  closed handles/pipes, terminated monitors, a fresh successful task after failure, redacted
  HTTP 503 and one persisted terminal event. Worker execution is released only after the
  cancellation boundary and monitor exist. Full regression and three real Ollama checks pass.
  This increment assumes available SQLite for failure persistence; atomic terminal writes,
  storage/monitor failure reconciliation, deadlines and replay remain in later increments.
- [x] **Second increment:** transact terminal task/message/event updates and handle monitor,
  pipe, storage and cancellation exceptions. Add readiness/heartbeat and phase-aware
  deadlines; represent approval waits separately.
  Verified 2026-10-22: first-winner SQLite transaction includes assistant metrics, final
  event and any planned goal checklist; rollback, contention, duplicate outcomes and restart
  recovery tests pass. Workers/Job descendants/pipes/handles are stopped before completion
  persistence; transient storage failure retries the outcome only, blocks new work and
  reports degraded health/runtime state. Readiness, heartbeat, model/tool/execution and
  total-task budgets apply; approval waits suspend active budgets but remain cancellable
  and expire safely. Thirty new tests, all existing regressions, live Ollama/UI, lint and
  frontend checks pass. Persistent inaccessible storage cannot commit an outcome: shutdown
  leaves it interrupted on the next working startup, never replays it. Replay is covered by the third increment below.
- [x] **Third increment:** paginate durable replay to a captured high-water mark, deduplicate
  events, bound slow clients, and explicitly recover from RAM cursor gaps.
  Verified 2026-10-22: fixed high-water replay in bounded acknowledged pages; durable store
  identity and backend epoch; no cursor rewind after deletion. RAM gaps send authoritative
  stream/approval snapshots, clear stale previews and catch up durable events. Actual
  SQLite/socket and rendered UI tests retain 5,001 unique events through disconnect and
  backend restart; slow peers time out without blocking health or skipping unacknowledged
  history. Token chunks stay in RAM; preview/approval history retains placeholders only.
  Fourteen new default checks, one opt-in real replay UI check and six Node tests pass.
- **Acceptance:** injected failures leave no stale running task or orphan; one terminal
  outcome per task; cancellation succeeds within five seconds in controlled fixtures;
  approval waits remain cancellable without a false timeout. Reconnection reproduces
  all durable events exactly once in UI state across 5,001 events and a backend restart;
  token/preview/approval bodies retain their intentional transient treatment.
- **Increment boundary:** all three P0-02 increments are complete at their stated test
  scope. Activity retention/delivery limits are documented in docs/desktop.md; no unlimited
  UI history, native/install validation, checkpoint/resume, scheduler or tool-policy expansion
  is claimed. Persistent inaccessible storage remains a reported external failure.
- **Tests:** spawn/send/thread/SQL fault injection, hung model/adapter, concurrent stop/result,
  duplicate cursor, restart and slow WebSocket client. No blind tool replay.
- **Dependencies:** existing Manager/Store/process layer. **Contracts:** F01; R1–R3.

### P0-03 — Bind approvals to reviewed resource state

- [x] **First increment:** fingerprint file preimages and the Git index/tree; revalidate after
  approval and immediately before mutation. Return a conflict and fresh review when changed.
  Verified 2026-10-22: identity/content versions for reviewed file bytes, Git index/HEAD
  and HEAD tree; stage input checks; trusted Studio creation review moved inside Coding.
  Changed/deleted/recreated files, identical index replacement and concurrent commits deny
  stale approval without mutation. Ten new cases plus original coding/worker/security,
  full regression, actual Ollama/UI and Ruff pass. Atomic publication and stronger Git
  local-configuration restrictions remain in the second increment.
- [x] **Second increment:** exclusive download publication and atomic reviewed writes with
  explicit symlink/reparse/hardlink defenses. Review Git local-config execution surfaces,
  including filters and signing helpers, beyond the already disabled hooks/fsmonitor.
  Verified 2026-10-22: checked same-directory staging; Windows replacement retains DACL
  entries/protection, new artifacts publish via exclusive hardlink creation. Existing/late
  download destinations survive; owned temporary files clean up after success/failure.
  Write and Git metadata paths reject symlinks/reparse points; actual junction/hardlink
  defenses pass. Git rejects executable filters, textconv/signing helpers and includes;
  disables signing/auto-maintenance/log signature helpers and rechecks effective config
  after approval. External worktrees cannot widen read scope. Twelve new default checks,
  three opt-in real download checks, full regression, actual Ollama/UI/coding and Ruff pass.
- **Acceptance:** a file/index/destination changed while approval is pending is never
  overwritten/committed under that stale approval. Denial, replay and expired approvals
  still execute nothing. Deliberately configured test helper programs cannot execute
  outside the reviewed execution policy. Document remaining host race/isolation limits.
- **Tests:** change/delete/recreate between review and approval; pre-existing and late
  download destinations; index swaps, malicious local Git configuration, link/junction cases.
- **Dependencies:** existing Policy/Coding/Browser; no new general shell escape hatch.
  **Contracts:** F02; R4/R7.

### P0-04 — Fix streaming privacy and visual-context regressions

- [x] **First increment:** stateful bounded streaming treatment for supported credential
  patterns; align live display, events and persisted-message behavior.
  Verified 2026-10-22: shared bounded parser for password/passwd/API-key/token/secret,
  JSON quoted values, Bearer and private-key blocks. Sixteen-character ordinary lookbehind;
  at most 128 retained characters, including incomplete headers. Secret values are discarded
  before token emission; shared complete-text treatment keeps final storage aligned.
  Nine new cases include every two-chunk boundary/character chunks, escaped quotes, long
  values/whitespace, cancellation and actual spawned-worker live/SQLite leak checks.
  Existing chunk-count assertion now checks exact combined text rather than raw frame count;
  token metrics and no-token-persistence assertions remain. Full regression, live UI and
  Ruff pass. Unknown formats, arbitrary credentials and screenshot pixels are not covered.
- [x] **Second increment:** retain original user images when adding tool screenshots;
  explicitly budget/discard only transient observations and safely clean orphan screenshots.
  Verified 2026-10-22: original images survive repeated observations; one normalized
  transient image shares the eight-image budget with originals. Explicit omission notices,
  owned capture registry/leases, identity/link checks, cancellation/startup compensation
  and abandoned-run cleanup pass targeted tests. Two actual Qwen3.5/Edge checks pass,
  including spawned Studio preview delivery and byte-identical attachment preservation.
  Cleanup refuses unknown/replaced files; no broad legacy screenshot sweep or physical
  desktop capture acceptance is claimed. P0-04 is complete at this stated scope.
- **Acceptance:** synthetic supported secrets split at every chunk boundary never appear
  raw in live events or stored output; buffering has a documented upper bound. An agent
  can use its attached image after taking a browser/desktop screenshot. Cleanup removes
  only known owned transient files; selected chat attachments survive.
- **Tests:** split-key/value/bearer patterns, adversarial long input, partial stream/cancel,
  image-plus-screenshot follow-up, image-count limits and interrupted cleanup.
- **Dependencies:** current worker/model/attachment code. Redaction remains best effort,
  not a guarantee for arbitrary credentials or screenshot pixels. **Contracts:** F03; R5/R6.

### P0-05 — Validate the native product and finish release packaging

- [x] **First increment:** preserve bounded redacted backend/model diagnostics and explicit
  dependency/port failures; verify single-instance, EOF shutdown and owned child cleanup.
  Add bounded backend restart with backoff and a manual fallback; interrupt tasks, never replay.
  Closed2026-10-27 using component/frozen checks plus owner-native/independent evidence:
  existing-instance focus, normal shutdown/reopen, idle/pending-approval crash recovery,
  no replay/fresh review and measured retry exhaustion/manual restart. Installed binaries
  match release expectations; no persistent duplicate/listener remains. This closure is
  first-increment scope, not full installation/upgrade or every active-effect certification.
  See .runtime/p0-05-native-lifecycle-acceptance/validation.json. Historical limits follow.
  Implementation verified at component/browser scope (2026-10-22): bounded redacted
  native/model diagnostics, serialized owned startup, child reaping, 1/2/4-second recovery
  budget, manual fallback and actual runtime EOF/port failure checks. Default: 195 passed /
  24 skipped; Rust four, Node seven, actual Ollama/UI six passed. **Native gate remains open:**
  second-instance check exited before readiness with WebView2 0x800700AA while the user's
  existing instance remained running. No native single-instance or crash/recovery pass is
  inferred. Keep unchecked; proceed independently with packaging/frozen-worker validation.
  Rechecked after P2-02(2026-10-26): input-desktop handle access and isolated UIA import
  pass, but owned native accessibility/bootstrap probes remain inconclusive; no frontend
  request within12s. Managed thread desktop is CodexSandboxDesktop-..., input is Default.
  Exact startup stall remains undiagnosed. No native acceptance, desktop reassignment or
  additional application change is inferred. See .runtime/roadmap-gates/after-mcp-20261026/.
  - [x] Installed second-launch focus/no persistent duplicate: owner observes the existing
    window focused; post-launch process/listener inspection finds the same original native,
    PyInstaller pair and Ollama PIDs, with one backend listener. No continuous transient-
    process trace is claimed. Evidence: .runtime/p0-05-native-second-instance/observation.json.
  - [x] Installed idle normal-close cleanup: after owner closes Studio, all recorded native,
    backend pair and owned Ollama PIDs exit, with both ports released. No observer kills.
    Shutdown latency/unrelated-process preservation are untested by this run; full native
    recovery/active-work shutdown remain open. Evidence: .runtime/p0-05-native-normal-shutdown/.
  - [x] Normal reopen startup/generation and persisted history: new native/backend/owned-
    Ollama chain, completed Chat generation and all pre-close record identity sets verified.
    Older-transcript rendering, exact reply compliance, crash recovery and upgrade remain
    separate. Evidence: .runtime/p0-05-native-reopen/.
  - [x] Installed idle backend-crash recovery: owner reports reconnection and independent
    inspection finds the same native instance with a fresh owned backend/model chain, old
    children gone, one listener per service and retained history with no new task/operation.
    Active-work interruption/no-replay and native retry timing/fallback remain separate.
    Evidence: .runtime/p0-05-native-idle-crash-recovery/validation.json.
  - [x] Installed pending-approval crash interruption/no replay: captured waiting task
    becomes interrupted; target remains absent, old task worker exits, and no new task/
    operation/verifier or approval-resolution record appears. Unfinished write remains
    unknown. Fresh resubmission approval and native retry/fallback timing remain separate.
    Evidence: .runtime/p0-05-native-pending-crash/validation.json.
  - [x] Fresh approval after native crash: distinct resubmitted Agent task requests one
    new approval and records denial, with real model calls and no file/verifier. Original
    interrupted task remains unchanged; pre-request history identities persist. Native
    retry exhaustion/manual restart and full first/third remain separate. Evidence:
    .runtime/p0-05-native-recovery-fresh-denial/installed-observation.json.
  - [x] Native retry exhaustion/manual fallback: installed owner run records four failures
    with1.094892/2.019097/4.047970-second gap lower bounds, quiet budget exhaustion, one
    manual launch/connection and normal-close descendants gone before fixture cleanup.
    Independent Python survives. Owner observes native UI; process/timing/hash data support
    the report. Earlier failed run remains retained. Evidence:
    .runtime/native-recovery-e7420e8c254e4ef59feb27380e4dc20f/report.json.
  - [x] Native diagnostic prerequisite: fixed development executable, owned isolated
    profile/static loopback page, bounded observation/log classification, content-free
    report, raw-log identity checks/removal, and refusal to touch existing Studio or
    occupied frontend/backend ports. Verify deadline/child cleanup, privacy, hardlinks,
    malformed/truncated logs and slow HTTP shutdown. Actual diagnostic reports GPU
    subprocess access denial0xc0000022 and unusable GPU; temporary --disable-gpu also
    failed, with no production flag/default change.13 focused including actual diagnostic
    pass; default692 passed/65 skipped; Ruff/lock/wheel/import pass. No native IPC,
    single-instance/crash/UI, installer or upgrade acceptance is inferred.66 previously
    verified runtime modules remain byte-identical. See docs/native-diagnostics.md.
- [x] **Second increment:** run the existing PyInstaller/NSIS build, validate frozen worker
  spawning, external coding Python, browser discovery and first-run configuration.
  Implemented/verified 2026-10-22: actual PyInstaller sidecar, optimized release EXE,
  frozen worker/approved external Python/restart persistence, actual model-driven Edge
  navigation/screenshot and exclusive default config publication. Final frozen checks:
  15 passed; Rust seven; default 197 passed / 26 skipped. Checksums/build manifest generated.
  **External blocker:** NSIS 3.13 download denied with socket error 10013 in both bundling
  attempts. Full build correctly fails with an explicit partial manifest. No installer,
  clean-install or upgrade pass; keep unchecked. Normal permitted-network rebuild steps
  are in docs/desktop.md. Continue independent P1-01 while P0-05 native/install gates remain.
  Partial refresh2026-10-26: current B2b assets and B2a source-equal sidecar build into the
  optimized release candidate offline. Deployed runtime/socket/approved-coding6/6 pass;
  exact archive readbacks pass. Fresh upstream NSIS3.13 acquisition still fails10013.
  Existing app/window access prevents native acceptance; no installer or upgrade pass.
  See .runtime/roadmap-gates/after-memory-20261026/release-validation.json.
  Owner build recovery2026-10-26: real NSIS installer is produced,77,019,958 bytes,
  SHA266fa4cf24a830cb4df08a7cd02ec5c60562f370e7cad3d8ab6cc360a35f66c7.
  All115 manifest inputs/3 artifact hashes and61 frozen code modules match current source;
  deployment copies/template match.17 frozen runtime/socket/live-browser/approved-coding,
  1 frozen MCP and7 Rust checks pass, zero skips. Packaging increment now closes;
  installer execution/payload-after-install/native acceptance/upgrade remain third/first.
  Evidence: .runtime/p0-05-owner-installer-verification/validation.json.
- [x] **Third increment:** install as a standard user and repeat core native flows, including
  physical dialog/clipboard/capture/export and approval/cancel behavior.
  Verified2026-10-28 in the dedicated Standard-user VM: real installed WebView/IPC/Ollama,
  exact denial/approval evidence, physical picker/clipboard, capture/preview/export, Stop,
  changed preference, actual0.1.0→0.1.1 upgrade, logical config/history/attachment retention,
  real post-upgrade/reinstall replies, default and explicit-data-delete native uninstall.
  Original146/current162 records are preserved at their respective comparison boundaries;
  outside files and independent Ollama survive. Guest fixture tasks/processes/listeners
  are cleaned.54 regression passes/1 skipped, Ruff passes. Initial clean setup includes
  owner observations followed by independent installed evidence. Test0.1.1 is not a public
  release. See IMPLEMENTATION.md and .runtime/p0-05-vm-acceptance/validation.json.
  Historical partial observations follow; their outstanding third-increment claims are
  superseded by the completed guest matrix.
  Partial recovery verified2026-10-26: corrected installed code/config, settings backup
  preservation, automatic Studio-owned Ollama and a reported330-token chat. Real browser
  and memory workflows each pass against that installed executable in disposable fixtures.
  These do not prove native controls or clean-install/upgrade/history acceptance; keep open.
  Later owner confirmation: visible reply, Copy and Stop work in the installed native app.
  Approval/recovery/second-instance/physical controls and upgrade/data retention still need
  acceptance. Installed native hash matches the separately derived NSIS payload expectation;
  raw build-artifact hashes remain unchanged. Keep first/third open for remaining criteria.
  - [x] Installed Agent file-creation approval: owner denies, then resubmits and approves
    a fresh request. Independent durable decisions/journal/verifier records and exact18-byte
    readback confirm the sequence. Denied task has no artifact record; approved task has
    one passed record matching the file SHA. This closes this subcheck only; dialog operation
    is owner-observed. Evidence: .runtime/p0-05-native-approval-verified/installed-observation.json.
  - [x] Native file chooser and text attachment: owner confirms Windows picker operation;
    fixture text/hash, message binding and matching actual-model Chat reply are independently
    verified. Raw text upload bytes are intentionally not retained separately from sanitized
    text. Capture/preview/export and full third acceptance remain separate. Evidence:
    .runtime/p0-05-native-attachment-acceptance/validation.json.
  - [x] Native conversation export/download: actual saved Markdown in Downloads matches
    the complete two-message official export byte-for-byte (208 UTF-8 bytes); attachment
    body excluded. Owner action plus independent readback verify delivery. Save As dialog
    behavior is not inferred. Evidence: .runtime/p0-05-native-export-acceptance/validation.json.
  - [x] Native screenshot capture and image preview: owner confirms the installed preview
    appears. Read-only installed metadata verifies two new screenshot.jpg JPEGs,1600x900,
    matching stored sizes/hashes. Images remain unbound; no model-image submission is
    claimed. Raw images are not exported, temporary database snapshot removed. Evidence:
    .runtime/p0-05-native-capture-acceptance/validation.json.
  - [x] Preserve independently running Ollama on native normal close: actual installed owner
    run1d6ac6dd25ce42ce824c8b54a294e4a0 passes after the startup-race correction. Independent
    fixture identity/listener/health survive X close before its separate harness cleanup;
    captured native children exit first. Tested source and installed hashes match; fresh
    process/listener check is empty after cleanup. Scope is normal close, not every active
    task effect or unrelated-service configuration. Do not repeat unnecessarily. Evidence:
    .runtime/p0-05-native-shared-model-acceptance/validation.json and docs/native-shared-model-check.md.
  - [x] Upgrade-test artifact prerequisite: isolated0.1.1 packaging-only NSIS fixture and
    original0.1.0 installer have recorded hashes; original build inputs remain unchanged.
    Seven native Rust tests pass after supplying the fixture's missing test-only Python
    environment. This is build/test preparation, not standard-user install/upgrade acceptance.
    See .runtime/p0-05-install-upgrade-fixture/build-result.json and docs/windows-test-vm.md.
- **Acceptance:** NSIS artifact with checksum and dependency manifest; clean install launches
  chat and an approved real tool workflow; no separate backend/model terminal needed.
  Startup failure is actionable, recovery is bounded, a second instance creates no backend,
  shutdown leaves no owned workers, unrelated Python/Ollama remain running, and existing
  configuration/history survive a tested upgrade. State/document uninstall data behavior.
- **Tests:** native WebView2 acceptance, process-tree observation, crash/port collision/missing
  runtime/offline launch, clean VM install/upgrade. Frontend browser IPC bridge is insufficient.
- **Dependencies:** Windows packaging toolchain and interactive test machine/VM; signed public
  distribution may require a separately approved signing identity. Do not block local NSIS
  validation on a signing purchase. **Contracts:** F01/F11/F12; R10.

## P1 — High-value platform capabilities

### P1-01 — Typed registry and explicit capability profiles

- [x] **Smallest increment:** wrap the 19 existing functions in versioned ToolSpec records;
  retain adapter code and approval behavior. Then add per-run allowed tool categories.
  Verified at the contract scope, 2026-10-23: immutable version-1 specs, pre-dispatch
  schema/type/default/command checks and category profiles in UI/API/CLI. Unified retains
  all categories; profiles persist per task and cannot widen on regeneration. Fourteen
  contract/process/migration/API/CLI checks, real approved-test UI and local Playwright
  checks, full default regression, TypeScript/Vite, Node and lint pass. The final 19
  model-facing schemas equal the saved baseline exactly. A supervisor PID-handoff test
  race was fixed without weakening cancellation/deadline assertions.
  **Separate validation limit:** actual model regressions were attempted and failed because
  the managed service cannot read the existing Qwen manifest; they are not counted as
  passes. Start the normal Windows service and rerun the documented live opt-ins. This
  checkbox covers the registry/profile contract, not new model-quality, native/installer,
  MCP or OS-isolation acceptance. Those gates remain separately open.
- **Acceptance/tests:** schema/default/error contract tests and all existing adapter tests
  pass; malformed arguments and tools outside a selected profile are denied before invoking
  adapters. Existing unified mode can explicitly retain all currently approved categories.
  Runtime configuration remains trusted; tool output cannot register providers or widen scope.
- **Depends on:** P0-03. **Contract:** F07. No MCP dependency required yet.

### P1-02 — Verifiers and practical coding workflow improvements

- [x] **Increment A:** persist verifier results separately from `reported` model prose; begin
  with artifact readback/hash and configured-test exit plus actual test-count checks.
- [x] **First verifier within A:** configured unittest execution records actual TestResult
  counts independently of model/console prose. Verified 2026-10-23: passing/failing/zero/
  skipped/expected-failure cases, spoofed output, early exit, stale bytecode, truncation,
  approval denial and helper review conflicts. Separate SQLite evidence/event transaction,
  authenticated retrieval, restart retention, chat deletion, cancellation and secret-output
  tests pass. Eighteen new checks; full default 229 passed / 27 skipped; rendered real
  approval/test/evidence UI, five rebuilt frozen-backend cases, TS/Vite/Node/lint pass.
  This is an observed test run, not whole-task certification or hostile-process attestation.
  Unsupported frameworks remain inconclusive. Artifact readback/hash is documented below;
  the original real-model gap is resolved by the counted acceptance entry below. Do not count
  blocked tests as passed. Temporary helper/count directories can remain after a hard crash.
- [x] **Artifact verifier within A:** compare approved coding-write/no-op bytes and SHA-256
  with bounded, policy-checked readback; retain file-version metadata independently of model
  prose. Verified 2026-10-23: exact Unicode/newline/empty/no-op cases, reviewed line-ending
  changes, missing/mismatched/unstable publications, hardlink/scope refusal, denial, safe
  metadata and authenticated durable history/deletion. Thirteen new cases; all 31 verifier
  checks, full default (242 passed / 28 skipped), two rendered UI scenarios, three rebuilt
  frozen-backend/UI cases, TS/Vite/Node/lint pass. No blind repair or replay. This proves
  point-in-time byte agreement, not code correctness, future freshness or whole-task success.
  Current counted model acceptance is now verified in the entry below.
- [x] **Increment B:** add bounded scoped repository search and reviewed patch sets with
  preimage conflicts; then stream bounded command output and expose background readiness.
- [x] **Scoped search within B:** literal case-sensitive UTF-8 search through existing
  file policy, with path/line/column/hash, sanitized previews and explicit coverage limits.
  Coding/Unified tool plus authenticated Workspace search/open-file UI. Verified 2026-10-23:
  17 search tests cover scoped reads, credentials/state/link exclusions, concurrent changes,
  byte/file/entry/depth/time/output limits, stop, authentication, profile denial and real
  worker execution. All 31 targeted cases, default regression (259 passed / 29 skipped),
  three rendered scenarios, seven rebuilt frozen-backend/UI checks, TS/Vite/Node/lint pass.
  No shell/regex/dependency added. Search is an observation within eligible text scope,
  not an OS sandbox, atomic repository snapshot or model-quality certification.
- [x] **Reviewed patch sets within B:** one create/replace review for up to eight related
  UTF-8 files; expected raw-byte hashes and approval-time identity/content versions.
  All preimages revalidate before first publication, then pending files revalidate during
  execution. Conflicts/denial preserve existing files; incomplete outcomes report written,
  uncertain and pending paths and stop automatic agent continuation. Each successful
  readback persists existing artifact evidence. Verified 2026-10-23: 17 new patch cases,
  91 targeted checks, default 276 passed / 30 skipped, four rendered scenarios, eight
  rebuilt frozen-backend/UI/runtime checks, TS/Vite/Node/lint pass. No destructive rollback
  or cross-file atomicity claim. Deletion/rename and crash journals are outside this adapter;
  test execution still requires its own approval. Current model acceptance is recorded below.
- [x] **Foreground command streaming within B:** bounded merged pipe capture, redaction
  before worker events, at most 64 ordered durable deltas and a 16,000-byte display prefix.
  Scoped latest-three command panel reconstructs persisted output, flags truncation/gaps
  and distinguishes interrupted unknown outcomes from observed exits and test verification.
  Verified 2026-10-23: 15 new stream cases; all 83 targeted checks, full regression
  (291 passed / 32 skipped), six rendered scenarios and ten rebuilt frozen-backend/UI/
  runtime checks pass; TS/Vite/Node/lint pass. Windows owned-child cleanup and startup faults,
  timeout/stop, secret boundaries, reconnect and raw Git-policy parsing regressions pass.
  Subsequent background output/readiness and current model acceptance are recorded below.
- [x] **Owned background output/readiness within B:** replace output spooling with shared
  bounded capture/publisher, owned lifecycle monitoring and command_status inspection.
  Optional trusted literal-loopback HTTP checks require listener-tree ownership, exact
  status and bounded startup/probe budgets; no URL/PID tool arguments, redirects or bodies.
  Unconfigured starts never claim readiness. UI retains timestamped observations, recent
  commands and active owned servers. Verified 2026-10-23: 20 new cases; all 58 targeted
  checks, final default 311 passed / 34 skipped, eight rendered scenarios, twelve rebuilt
  frozen-backend/UI/runtime checks, TS/Vite/eleven Node/Ruff pass. Includes IPv4/IPv6,
  unrelated-listener denial, slow/trickling headers, faults and actual server/test cleanup.
  Task lifetime only; no OS-isolation, continuous health or model-quality claim. All initial
  A/B engineering components are implemented; the remaining model/count gate is resolved below.
- [x] **Counted current-model acceptance (2026-10-23):** fixture uses the supported canonical
  unittest profile and approves only the actual trusted helper/code/private paths/nonce/cwd,
  while retaining its human grant. Real Qwen counter run passed in 23.628s: initial structured
  3 tests / 1 failure, final 8 passed, independent counted rerun 8 passed, separate oracle
  6 passed, seed tests unchanged and diff reviewed. Four new denial/false-count cases and
  all verifier/default regressions pass: 370 default passed / 37 skipped, 28 targeted passed /
  1 skipped, Ruff pass. No production adapter or unsupported-profile semantics changed.
  A/B acceptance is satisfied at these scopes; P1-04's dependency is now met. No native
  install, OS isolation, universal model reliability or whole-task certificate is inferred.
- **Acceptance/tests:** a seeded real-model counter task passes its independent tests and
  reviewed diff; intentional failing tests, zero-test discovery and a false model success
  never become verified. Concurrent edits block patch application. Cancellation truncates
  logs safely and cleans owned servers; secret canaries do not enter diagnostic output.
- **Depends on:** P0-02/03/04, P1-01; retain approval for executable tests.
  **Contract:** F04. First PR need only introduce one verifier and its failure tests.

### P1-03 — Project-scoped memory, then semantic retrieval

- [x] **Increment A:** explicit remember/search/forget records in SQLite, source provenance,
  scope and deletion; use keyword retrieval before embeddings.
  Implemented and verified at storage/API/worker/rendered/frozen scopes (2026-10-24),
  including 32-question retrieval, provenance, source-chat cascade, scoped ID access,
  fresh tool approvals and exclusion of old model history/generated checklists on forget.
  Current real-model revalidation passed2026-10-24 against the existing local service:
  exact saved color/citation after backend and conversation restart; confirmed forget
  excludes retrieval and prior model context (1 passed,3.417s). Current522-test default
  regression includes32/32 scoped lexical recall, and all36 frozen checks include memory
  UI flows. A is complete at this explicit-memory scope. Earlier owned-startup manifest
  Access is denied logs remain; existing-service use does not diagnose that cause.
- [x] **Increment B:** evaluated local embedding model, chunk/version/hash tracking and
  bounded vector similarity, combining lexical and semantic results only when beneficial.
  Ordinary owner-session installation succeeded2026-10-26. The existing service now has
  qwen3-embedding:0.6b (1024 dimensions); the first fixed actual-model comparison passes:
  literal32/32 unchanged, paraphrase hybrid30/32 versus lexical14/32, cross-project0.
  B0 is the initial evaluation; B1/B2/B3 below provide the integrated acceptance evidence.
  - [x] B0: bounded local embedding client and immutable paired retrieval evaluation.
    Verified773 default tests/707 passed/66 skipped,53 focused/50 passed/3 skipped,
    actual embedding contract1 passed; Ruff, lock and source-equal69-module wheel pass.
    Final numeric-guard checks15 passed/1 opt-in skip; no skipped case is a pass.
    Evidence: .runtime/p1-03-embedding-evaluation/validation.json.
  - [x] B1a: persisted note-vector index, explicit authenticated reindex/search, identity/hash/epoch
    validation and deletion cascade, without network inference under the admission lock.
    Verified790-case regression/723 passed/67 skipped;164 focused/161 passed/3 skipped;
    SQL publication-fault check1 passed separately after default discovery. Actual model
    contracts2 passed; actual frozen API/restart/forget1 passed; frozen approved coding1
    passed. Twenty repeated cancellation checks pass after fixing Windows buffered reads.
    Ruff/lock,71-module source-equal wheel and59 source-equal frozen modules pass.
    Evidence: .runtime/p1-03-note-index/validation.json. Automatic prompt/UI remains B1b.
  - [x] B1b: explicitly enabled automatic hybrid Studio retrieval and index controls, with
    snapshot revalidation and visible stale/reindex status. Verified808 default tests/739
    passed/69 skipped;159 focused/155 passed/4 skipped;23 frontend utility tests and
    TypeScript/Vite build pass. Actual source/frozen chat recall after restart, citation,
    forget and stale refusal each pass; rendered source/frozen controls and legacy UI/
    coding regressions pass. Ruff/lock and source-equal72-module wheel/60-module frozen
    backend pass. Evidence: .runtime/p1-03-memory-integration/validation.json.
  - [x] B2a: explicit approved text-file preview/import API, bounded chunks with source
    spans/hash/version, scoped deletion and changed/missing/unsafe-source invalidation.
    Reuse existing scoped reads; no crawler, file writes or stale recall.
    Verified836 default tests/765 passed/71 skipped; actual source/frozen workflows and
    rendered provenance/whole-source forgetting pass. Schema10 rollback, scope/credential/
    cache-corruption guards, changed-source history invalidation and populated backup/
    restore/retention pass. Evidence: .runtime/p1-03-memory-sources/validation.json.
  - [x] B2b: source-selection/review/provenance controls and their rendered acceptance;
    expose import, stale status, reimport and confirmed whole-source forgetting.
    Verified source/frozen preview/cancel/import/conflict/reimport/forget workflows,
    blank-conversation/900px review and delayed old-scope preview/metadata rejection.
    76 focused tests/72 passed/4 skipped;23 frontend tests, Ruff and TS/Vite runner build
    pass. Backend unchanged from B2a. Evidence: .runtime/p1-03-memory-source-ui/validation.json.
  - [x] B3: actual restart/citation/forget/source-change acceptance and rendered/frozen checks
    for the integrated feature. Fixed production file-backed comparison after restart:
    literal32/32, paraphrase30/32 (93.75%) versus keyword14/32, cross-project0; actual
    chat citation/source spans, stale history/vector exclusion, whole-source forget and
    source-chat cleanup pass.89 focused tests83 passed/6 skipped; Ruff passes. Reuses
    unchanged B2a real frozen workflow and B2b rendered source/frozen checks. No quality
    retuning/retry; Zephyr/Acorn remain misses. Evidence: .runtime/p1-03-memory-acceptance/validation.json.
  Prior managed registry10013 acquisition failures remain historical evidence; availability
  is now resolved by the owner's ordinary pull, without changing managed network controls.
- **Acceptance/tests:** recall across backend/conversation restarts with visible citations;
  recall@5 >=0.90 on at least 30 seeded questions; zero unauthorized cross-project results.
  Forget/chat deletion removes derived vectors, modified files invalidate stale chunks,
  embedding-model changes require reindex, and malicious retrieved text grants no authority.
- **Depends on:** P1-01/05, explicit approved text scope, local model availability. No cloud
  embedding fallback or initial vector server. **Contract:** F05.

### P1-04 — Durable execution journal and honest recovery UI

- [x] **Smallest increment:** numbered schema migrations plus run/step/tool intent/result
  records and effect classes. Display interrupted steps and artifact preconditions.
  Offer inspect/reconcile/new-run, without claiming checkpoint resume.
- **Verified 2026-10-23:** schema v1/v2 legacy adoption and transactional rollback preserve
  chats/goals/attachments/identity/cursors. Committed intents gate tool dispatch, committed
  results gate continuation; hashes and transient approvals grant no later authority.
  Forced `os._exit` at all four boundaries, storage/ack faults and restart show completed,
  interrupted or unknown work with no replay. Authenticated inspection compares bounded
  present file state; manual reconciliation informs a new instruction without clearing
  uncertainty or submitting automatically. Source/frozen rendered UI and actual Ollama
  integration pass; see IMPLEMENTATION.md and docs/execution-journal.md. Standalone CLI
  retains its audit; cleanup, checkpoint resume, OS isolation and installers are distinct.
- **Acceptance/tests:** force process exit before intent, during execution, after effect and
  after result commit. Every step becomes completed, interrupted or unknown with evidence;
  no action is replayed. Approval bodies remain transient; persisted hashes cannot authorize
  a later task. Migrations preserve current conversations/goals/attachments.
- **Depends on:** P0-02/03 and P1-01/02. **Contract:** F06.

### P1-05 — Capability-aware inference and context management

- [x] **Increment A:** unified validated options/capability cache, explicit max output,
  supported thinking/residency settings, finish reasons, and prompt/load/first-token timings.
- **A verification:** actual chat/plan/tool payloads share validated options. Local
  identity/version/TTL admission, incompatible tool/vision/schema/thinking and remote
  rejection have positive/negative/stale-metadata cases. Length-truncated tool calls
  never dispatch; safely redacted partial chat stays visibly incomplete. Stream timing
  distinguishes first thinking token from first visible content without persisting
  reasoning. Final default 421 passed / 42 skipped; five actual-model checks and 22 final
  frozen UI/runtime/socket checks passed. See IMPLEMENTATION.md and docs/inference-options.md.
- [x] **Increment B:** account for prompt/schema/output reserve and visual input; expose an
  estimate honestly if no exact tokenizer is available. Add bounded compaction that preserves
  the objective, approved scope and evidence references, with a visible context notice.
- **B verification:** shared versioned UTF-8/schema/image/template/output estimate, protected
  instructions/images/call groups, bounded untrusted excerpts and canonical verifier refs.
  Requests disable silent native truncation/shift; unfit protected/native context blocks.
  Numeric durable notices are scoped to the selected conversation. Final 439 passed /
  47 skipped; all six actual original/compacted semantic variants and three other final
  live regressions passed. Original-image, rendered/frozen, build/lint/Node checks pass.
  Earlier literal-field-name baseline failures are preserved, field mapping was clarified
  in both arms, exact approval/value/evidence checks retained and a negative regression
  rejects that same mistake. See IMPLEMENTATION.md and docs/context-budget.md for bounds.
- **Acceptance/tests:** settings appear in actual chat/plan/tool payloads; incompatible
  tool/vision/schema models fail admission clearly; length-truncated output is not marked
  complete. Exercise multilingual/code/image boundary inputs and stale capability metadata.
  Compare compacted versus original seeded tasks without a drop in required evidence checks.
- **Depends on:** P0-04, P1-08 baseline; official model capabilities and local measurements.
  Do not silently change models or global server configuration. **Contract:** F10; R9.

### P1-06 — Maintainable UI, scoped history and recoverable data

- [x] **Increment A:** extract chat/approval/task/workspace/model components and typed event
  contracts; scope activity and screenshot previews to the selected task/conversation.
  Verified 2026-10-24: six integrated views, guarded unknown event payloads, selected-task
  membership and task-owned transient previews; global approval/stop retained. All 33
  frozen UI/runtime/socket/loop checks and 18 Node checks pass; default 456 passed /
  51 skipped. Sidecar code/source parity verified. See IMPLEMENTATION.md and
  docs/studio-activity.md. No native installer, current model or B acceptance claim.
- [x] **Increment B:** paged history, accessible focus trapping/return, keyboard navigation
  and a responsive activity drawer; then explicit SQLite online backup/validated restore
  and user-configured retention with preview/confirmation.
  - [x] **B1 — dialog/activity access:** native modal focus containment/return, safe Escape,
    keyboard navigation and a 900px activity drawer, including global approvals/stop.
    Verified 2026-10-24: all34 frozen UI/runtime checks, actual keyboard/visual scenario,
    TS/Vite/Node/Ruff; default 456 passed / 52 skipped. Model/native IPC in UI use fixtures;
    native installed-product acceptance remains separate.
  - [x] **B2 — bounded history paging:** cursor-based conversations/messages/tasks and
    explicit older-page controls without losing selected-task context or loading all rows.
    - [x] B2a: verified bounded authenticated API/index migration, preserving legacy routes
      and model context.
      Verified2026-10-24: 231-row/timestamp/cursor/scope fixtures, real205-message HTTP
      traversal, auth negatives, v3 rollback/preservation and indexed query plans; all30
      source targeted/35 frozen checks, Ruff and default468 passed /52 skipped. See
      docs/history-paging.md; no UI paging or byte-bounded snapshot claim.
    - [x] B2b: integrate paged desktop controls and selection/replay/export.
      - [x] Conversation sidebar/search/selected metadata verified2026-10-24:72 actual
        chats, bounded requests, delayed-response rejection, selected pin, rename/new/
        delete/reload, all36 frozen checks and default469 passed /53 skipped. See
        IMPLEMENTATION.md and .runtime/p1-06-conversations/validation.json.
      - [x] Message paging and complete, explicitly bounded export, including selection/
        reconnect/late-response tests and preservation of existing command/approval flows.
        Implemented:529 default/475 passed/54 skipped, all37 frozen and final3 affected
        packaged cases, TS/Vite/18 Node/Ruff and18 code/source matches. Initially actual
        UI2 failed because the service disappeared and owned startup logged manifest
        Access is denied. Those failed runs remain. Recovery2026-10-25: both actual-model
        UI scenarios now pass/zero skipped;20 history,3 discovery and3 source/3 packaged
        affected UI checks pass. Only the scoped browser test fixture changed, adding an
        owned origin and stronger content assertions; runtime/frontend/binary match B1.
      - [x] Task-history paging beyond200, preserving selected-run details/replay and
        global active tasks, approvals and emergency stop.
        Verified2026-10-24:251-row/six-page rendered traversal, older selection/reconnect,
        owned backdated workers, approval denial/stop and late deleted-chat404 handling.
        Default477 passed/55 skipped; all38 packaged checks and final3 affected UI cases,
        source44 passed/3 skipped, TS/Vite/19 Node/Ruff;19 sidecar code/source matches.
        Evidence: IMPLEMENTATION.md and .runtime/p1-06-tasks/validation.json.
      All three paging components and complete bounded export are now verified.
      Native installed-product acceptance remains separate from this source/browser scope.
  - [x] **B3 — backup/restore:** online consistent snapshot, validated staged restore into
    fresh state, rollback copy/explicit confirmation, and active-task refusal.
    - [x] B3a: confirmed online backup to fixed app-owned storage; integrity/schema and
      bounded-size/runtime checks, active-owner refusal, settings control and tests.
      Verified2026-10-24: final39 targeted, source rendered1 and all39 packaged checks pass
      without skips; default488 passed/56 skipped, TS/Vite/19 Node/Ruff and20 sidecar
      source matches. Complete table/WAL/binary preservation plus denial/conflict tests.
      See docs/studio-backups.md and .runtime/p1-06-backup/validation.json.
    - [x] B3b: validated staged restore, rollback snapshot, explicit confirmation and
      fresh-state/restart verification; corrupt/incompatible input must preserve live data.
      - [x] B3b1: bounded authenticated restore preparation into fresh app-owned state,
        reviewed schema/integrity/hash validation and rollback copy; never activate a draft.
        Verified2026-10-24: all54 targeted and18 packaged runtime/HTTP checks; default503
        passed/56 skipped, Ruff,21 sidecar matches, unchanged frontend parity. Nonempty
        table preservation, actual crash points and negative input/ownership/cleanup checks
        pass. Evidence: .runtime/p1-06-restore-stage/validation.json; activated:false only.
      - [x] B3b2: confirmed activation/restart, safe current-state routing and rollback UX,
        fresh identity/event reset, real runtime/rendered verification and crash boundaries.
        Verified2026-10-24: default527 passed/57 skipped; all79 targeted, restored-worker1,
        and43 packaged checks pass; TS/Vite/19 Node/Ruff and24 runtime code matches.
        Two actual backend restarts plus900px keyboard/stale-response and before/after
        publication crash gates pass. Native IPC/inference are fixtures in rendered tests;
        installed-product/model gates remain separate. See IMPLEMENTATION.md and
        .runtime/p1-06-restore-activation/validation.json.
  - [x] **B4 — retention:** user-configured preview/confirmation; preserve active tasks and
    project files, respect memory provenance and state explicit export/deletion limits.
    Verified2026-10-25: saved age/recent/batch policy, exact five-minute reviews and explicit
    confirmation; atomic dependent-record cascades and kept-chat memory-context invalidation.
    Selected/recent/unfinished/pending/active work is protected; project files, backups and
    generations remain. Final default540 passed/58 skipped,90 targeted and45 packaged
    checks without skips; TS/Vite/19 Node/Ruff and25 runtime code matches. No automatic
    cleanup or secure-erasure claim. See docs/studio-retention.md and
    .runtime/p1-06-retention/validation.json. The later actual-model UI recovery above
    satisfies the final B2b/B2/B gate; earlier retained evidence is unchanged.
- **Acceptance/tests:** current live UI scenario stays passing; 900px-wide window can access
  activity/approvals; keyboard users can operate and exit dialogs. Switching conversations
  shows no other task's stale preview. Backup restored into a fresh state directory retains
  chats, attachments, goals and preferences; corrupt/version-incompatible backups fail safely.
  Restore requires explicit confirmation, a validated staged database and a rollback backup;
  it must refuse while tasks are active and never take a model-supplied destination path.
  Retention never removes project files or active tasks; export limits are explicit.
- **Depends on:** P0-02/04 and migration discipline. Native installed-product acceptance
  remains P0-05; the earlier P0-06 reference had no corresponding roadmap item and is
  corrected here. Source/rendered UI refactoring does not close the native gate. **Contract:** F12.

### P1-07 — Optional OS-isolated execution for untrusted projects

- [ ] **Smallest increment:** define an execution-backend interface, label the current backend
  “trusted host execution,” and implement one explicitly configured disposable VM path.
  Start with code/test workflows; leave host desktop automation separate.
  In progress2026-10-28: actual management role/provider restored. A distinct, owned imported
  VM boots with bounded resources and host-enforced stateful SSH/deny-all ACLs; DHCP rules
  are removed afterward. Original release VM stays running. Backend/lease/staging/checkpoint/
  cancellation and full isolation acceptance remain unimplemented/unverified; do not close
  this checkbox from preparation/probes. See current IMPLEMENTATION.md checklist.
- **Acceptance/tests:** VM task cannot read/write host canary paths, inherit host secrets,
  or reach denied networks; only staged approved inputs/outputs cross the boundary. Cancel
  stops the owned VM task and does not affect unrelated processes. Unsupported host setup
  fails closed rather than silently using host execution for an isolation-required task.
- **Depends on:** P0-03, P1-01, supported virtualization/Windows edition and any required
  user-approved host setup. No claim that Job Objects supply this isolation. **Contract:** F02.
  Current2026-10-28: owner-created Windows release-test VM and verified Standard-user SSH
  are available, but host Get-VM still returns permission denial. No configured disposable
  agent-execution backend or enforced denied-network policy exists. Require supported
  administrator-backed VM control and a dedicated safe execution image/network; do not
  repurpose release-testing transport as an isolation guarantee or fall back to host tools.
  Current external gate(2026-10-25): no configured disposable VM provider/image; Get-VM,
  VBoxManage and vmrun are unavailable on this session PATH, and OS capability query is
  denied. Host support is unverified, not proven absent. Do not enable host features or
  claim isolation from this evidence; continue independent P2-01 while setup is unresolved.

### P1-08 — Agent evaluations and local observability

- [x] **Increment A:** run/step/tool correlation IDs, result taxonomy, latency breakdown and
  redacted diagnostic export; reuse current metrics rather than inventing another counter.
  Verified 2026-10-23 at Studio instrumentation/privacy scope: bounded run/plan/decision/
  model/tool/approval/cleanup spans, fixed failure categories, nested approval union,
  unknown interruption and verifier links. Authenticated snapshot/export excludes raw
  content/credentials and marks legacy/malformed/capped data. Seventeen new cases, all
  70 targeted checks, default 328 passed / 35 skipped, nine rendered scenarios, thirteen
  rebuilt frozen-backend/UI/runtime checks, TS/Vite/Node/Ruff pass. This checkbox does not
  establish corpus quality, p50/p95 model benchmarks, native install, durable operation
  intent/reconciliation, CLI trace export or whole-task certification.
- [x] **Increment B:** versioned evaluation corpus with at least 20 distinct tasks covering
  coding, browser fixtures, recovery, injection and denied operations; run model cases
  three times and keep deterministic security assertions separate from probabilistic quality.
  - [x] **First component - corpus/oracles/report contract (2026-10-23):** twenty model
    cases plus eight separate deterministic safety definitions; bounded strict schemas,
    independent file/JSON/AST/browser/tool observations and complete three-repeat matrix.
    Unknown/blocked/missing checks cannot pass; duplicate/mixed identities are rejected.
    Fixed-field reporting includes coverage, native counters, all-outcome p50/p95 and
    separate safety/quality gates; declared fixture inputs never establish model quality.
    Twenty new tests pass with actual browser denial enabled; default 347 passed / 36
    skipped, Ruff/wheel checks pass. Static Python oracles do not execute or semantically
    certify generated code. See docs/agent-evaluations.md and IMPLEMENTATION.md.
  - [x] **Execution adapter:** disposable workspaces, owned
    loopback fixtures (including injection), exact fixture-only grants, production
    Agent/Tools observations, effect guards, bounded cancellation/cleanup, actual
    model/settings/weights metadata and native usage. Preserve failed-case observations.
    Source, deadline/cancel, denied scopes, metadata/false-output and effect regressions
    pass; full protocol matrix 60/60 plus 8/8 safety. Real wheel contains matching source
    and loads independently. Actual runner is `python -m local_agent.evaluation_runner`.
  - [x] **Live acceptance:** run all twenty actual model cases three times plus all
    deterministic safety cases; verify the complete quality/security/performance gate.
    Verified actual `qwen3.5:9b` baseline: 55/60 (91.7%), 8/8 safety, zero critical/unknown
    effect observations; sixty complete latency/native samples. Five failures preserved
    with immutable-case/newline regressions; no oracle/grant relaxation. Scope remains
    these fixtures, not general correctness. See docs/agent-evaluation-baseline.md.
- **Acceptance/tests:** all deterministic safety checks pass; model success is >=90% on the
  versioned corpus with per-case outcomes and no critical unauthorized action. Report p50/p95
  latency, tokens, model/config/digest, failures and sample count; speed cannot mask failed
  verification. Diagnostic export has no raw launch token or seeded secret. Preserve failing
  cases as regressions. Thresholds are declared acceptance rules; observed results remain
  recorded separately and do not establish general task reliability.
- **Depends on:** P0-01/02/04 and P1-02 verifiers. **Contract:** F11.

## P2 — Advanced functionality after the foundations

### P2-01 — Checkpoint/resume for a supported subset

- [x] **Smallest increment:** checkpoint one read-only repository inspection workflow at a
  completed step boundary. Expose pause only after that boundary is acknowledged.
  Verified2026-10-25: selected-file model-driven inspection reuses Agent/worker/journal;
  schema5/version1 bounded checkpoints, deferred pause and explicit linked-task resume.
  Scope/file identity/content/model/version/memory/store checks refuse changed inputs.
  Only selected read_file calls are allowed; no approvals/hidden reasoning/handles or
  ordinary-mode continuation. Final default561 passed/59 skipped,48 packaged without
  skips;130 targeted plus late32/2 and source UI1 pass. TS/Vite/19 Node/Ruff,26 code
  matches. Actual runtime/worker crash and unrelated-process survival pass; inference/
  native IPC are explicit fixtures. See docs/inspection-checkpoints.md and
  .runtime/p2-01-checkpoints/validation.json; no actual-model quality/native release claim.
- **Acceptance/tests:** resume across worker/backend restart using versioned state and
  unchanged preconditions; changed input prompts reconciliation; no previously completed
  mutation repeats. External submissions, arbitrary commands and unsupported desktop/browser
  state remain interrupted/unknown. Stale approvals cannot authorize resume.
- **Depends on:** P1-04 and effect-specific verifiers. **Contract:** F06.

### P2-02 — MCP provider behind the existing policy

- [x] **Smallest increment:** one pinned, configured read-only local stdio server and a
  namespaced client adapter. Add other transports/side effects only for demonstrated needs.
  Verified2026-10-26 after the user acquired the isolated SDK: installed the pinned
  SDK from cache without upgrading working application dependencies. Opt-in
  mcp_project_read uses the shipped version1 stdio server in coding/unified profiles.
  Both sides enforce strict approved paths, links/credential/state exclusions and
  bounded UTF-8 reads. Identity/catalog changes require trusted review, with no
  automatic acceptance. Bounded framing precedes SDK parsing. Windows suspended
  spawn assigns the owned Job before execution; timeout/stop/close reap its tree.
  Existing API authentication, approvals and disabled tool behavior are preserved.
  744 default tests:680 passed/64 skipped; focused MCP15 passed/2 opt-in skips.
  Actual-model MCP, frozen MCP and frozen approved-test checks pass separately.
  Ruff, locked offline sync/check and source-equal packaged wheel pass. See docs/mcp.md
  and .runtime/p2-02-mcp-integration/validation.json. Other servers/transports are outside
  this increment; native installed-app/VM acceptance remains separate.
- **Acceptance/tests:** real handshake/list/call and bounded output; policy enforces approved
  paths/tools, schema changes trigger review, malformed results/timeouts fail safely, and
  cancellation closes only owned server processes. Models cannot add server commands/URLs.
- **Depends on:** P1-01/04/08, official compatible SDK and resource ownership. **Contract:** F07.
  Historical gate2026-10-25 (resolved by the SDK acquisition and verification above):
  official mcp2.3.0 was a pinned candidate, not installed or cached.
  Ordinary offline dry-runs found no cached SDK; online attempts failed socket10013.
  Those attempts did not verify compatibility or change the application. Preserve
  .runtime/p2-02-mcp/acquisition.json and .runtime/p2-04-review/preflight.json as history.
  The current real SDK/runtime verification above supersedes that acquisition blocker.

### P2-03 — Persistent schedules and approved-directory triggers

- [x] **Increment A:** one read-only interval task while Studio is running, with disable,
  timezone, explicit misfire behavior and persisted next run.
  - [x] A0 prerequisite: durable unique trigger IDs, bounded owned leases and atomic
    queue-to-task admission. Duplicate delivery/expired or abandoned claims must never
    launch a second task once a task ID is committed. Test rollback/crash/stop/conflicts.
    Verified schema6 private queue, exact request/owner/token binding, concurrent admission,
    real process crash/lost acknowledgement, retention and backup/restore integration.
    97 targeted/48 packaged checks pass;574 default passed/59 skipped. Queue-only scope,
    not exactly-once execution or automatic scheduling. See docs/workflow-queue.md.
  - [x] A1 integration: interval clock, persisted next run/misfire policy/timezone,
    disable and read-only coordinator workflow with actual runtime/UI verification.
    Verified schema7, UTC skip/latest-slot coalescing, one pending item per schedule,
    owned metadata preflight, restore drain and durable stop pause.597 default passed/
    60 skipped;131 targeted and52 packaged checks pass without skips. TS/Vite/23 Node/
    Ruff pass;30 archived code entries equal source. A/A1 close at runtime-only scope.
- [x] **Increment B:** debounced approved-directory changes with durable trigger IDs
  and self-output suppression, limited to selected-file read-only inspections while Studio runs.
  - [x] B0 prerequisite: bounded private directory snapshots, stable identity/content
    fingerprints and explicit incomplete observations. Verify real changes, concurrent
    replacement, credential/link/state/generated-output exclusions and all input budgets.
    Verified14 new cases/zero skipped;611 default passed/60 skipped;53 targeted passed/
    one legacy skip. Private source-only component, no timer or activated package adapter.
    Existing59 source files/assets/binary equal A1. See docs/directory-observations.md.
    Reopened and corrected during B1: a late directory addition could leave its stat
    signature unchanged. Filename revalidation now shares entry/time/STOP budgets;
    all15 snapshot cases, full regression and rebuilt packaged gates pass.
  - [x] B1 integration: persist baseline/debounce/trigger identity and integrate approved
    read-only dispatch/disable/stop/restore plus actual runtime/UI acceptance.
    Verified schema8 exact scope/source/queue binding, one pending run, restart/crash
    deduplication, owned bounded probes and fresh admission.638 default passed/61 skipped;
    172 targeted/56 packaged pass without skips;33 archived entries equal source.
    No between-poll capture, always-on service, automatic mutations or crashed-task replay.
- **Acceptance/tests:** duplicate delivery/restart causes one queued run per trigger ID;
  task/resource conflicts queue safely; DST and missed runs follow configured policy.
  Unattended sensitive work awaits real approval and expires safely. Disabled schedules
  produce no work. Closing Studio stops this first version; always-on operation is not implied.
- **Depends on:** P1-01/04, durable queue leases, P2-01 for any resumable job claims.
  **Contract:** F08. No unauthenticated external webhook.

### P2-04 — Restricted specialist review child

- [ ] **Smallest increment:** one read-only review child with a fixed contract, independent
  evidence and parent/child records. Keep execution serial initially.
  - [x] A0 prerequisite: fixed source-anchored report contract and seeded paired review
    trial. Compare one pass, same-agent self-review and an independent restricted review
    on identical inputs, with equal two-pass budgets for the latter two. Preserve controls,
    failures, model identity and measured overhead. Fixture/simulated results cannot prove
    a benefit. This development evaluator does not activate a Studio child or close P2-04.
    Verified2026-10-25: strict anchors/grants/provenance/native counters, source-version
    guards, owned bounded workers, eight fixture oracles and both actual24-input trials.
    Grounded specialist19/24 loses to self-review21/24 with two regressions; no benefit
    gate pass. Keep full Studio parent/child integration deferred for this candidate.
    See docs/specialist-review-trial.md and .runtime/p2-04-review-trial/validation.json.
    New-model feasibility2026-10-27: unchanged4B completion/schema-only trial completes
    all24 inputs/72 calls with identical settings/corpus hashes. Baseline17, self-review20,
    specialist20 exact-location matches; zero specialist wins/regressions means no benefit
    gate pass. This distinct candidate does not exceed retained9B self-review21/24 and is
    not adopted. No downloads/product changes or executed-workflow retries. P2-04 main
    stays open. Evidence: .runtime/p2-04-4b-review/validation.json and IMPLEMENTATION.md.
- **Acceptance/tests:** child permissions/budgets are subsets of parent's; deny mutations
  and recursive delegation; stop propagates and releases owned resources. Compare identical
  evaluation tasks against one agent; retain delegation only with a demonstrated quality
  benefit or clearer verified review and a documented latency cost.
- **Depends on:** P1-01/04/08, resource leases; no concurrent shared desktop or GPU assumption.
  **Contract:** F09.
  External gate2026-10-25: existing inspection worker is reusable but no specialist
  contract/records or paired review result exists yet. Configured model metadata times
  out without a listener. An owned portable-service check starts successfully but lists
  zero models and logs Access is denied; its owned process is closed cleanly. No inference,
  download, unrelated-process termination or permission change. Real-model comparison
  remains blocked; no child feature or benefit is claimed. Evidence:
  .runtime/p2-04-review/preflight.json and owned-model.json; recovery: docs/recovery.md.
  Three consecutive goal-turn audits confirm unchanged external prerequisites;
  blocked-audit-3.json records the latest check. Goal execution is blocked, not complete;
  resume after restoring approved model/SDK access. No remaining checkbox was closed.
  Later user-requested retry: configured existing Ollama0.40.7 now lists qwen3.5:9b,
  passes tools-metadata admission and completes an actual two-token OK text response.
  Model connection gate is restored; P2-04 implementation/paired comparison remains
  incomplete, and SDK/native/VM gates are separate. Evidence:
  .runtime/p2-04-review/model-restored-20261025.json. No checkbox was closed by this smoke check.

### P2-05 — Explicit local model routing

- [ ] **Smallest increment:** opt-in per-task-type local model profiles using measured
  capabilities and quality. User override wins; record why a model was chosen.
- **Acceptance/tests:** unsupported model never receives required tool/vision input; missing
  model reports actionable error without surprise download/cloud fallback; routing is stable,
  config changes are versioned and GPU loads serialized. Paired evaluations meet P1-08 quality
  gate and show task latency/memory costs, including load time.
- **Depends on:** P1-05/08 and at least two installed/evaluated candidates. **Contract:** F10.
  Readiness2026-10-26: official qwen3.5:4b tag exists with3.3–4.0GB variants. Candidate
  metadata/runtime compatibility/quality are not yet verified; there is still only one
  installed completion model. A reviewed fixed-corpus acquisition/evaluation plan is in
  .runtime/p2-05-second-model-readiness/plan.json. Explicit download permission is requested;
  no download, default change or routing implementation occurred before that prerequisite.
  Updated2026-10-27: owner explicitly approves acquisition/evaluation. Existing pull script
  succeeds; qwen3.5:4b Q4_K_M,3324173934 bytes, manifest d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04,
  advertises completion/tools/vision. Three actual structured/GPU, executed-tool/readback
  and vision tests pass, zero skips. Fixed60-model/eight-safety evaluation completed below;
  no route/default change. See .runtime/p2-05-candidate-4b/.
  - [x] Second-candidate acquisition/evaluation prerequisite: all60 actual first executions
    have native metrics/oracles;53 passed,5 failed,2 blocked. Eight safety cases pass, all
    effect observations clear. Eight slots originally stopped by pre-dispatch snapshot
    guards execute only after bounded observation retry is fixed; all actually executed
    negative outcomes remain identical, no workflow retries. Original unaccepted report
    and completion provenance are retained. The candidate fails the existing quality gate
    and is not adopted for routing. No paired9B/4B latency benefit is claimed. This closes
    the measurement prerequisite only, not P2-05. Evidence:
    .runtime/p2-05-candidate-4b/validation.json and IMPLEMENTATION.md.

## P3 — Optional enhancements with measured demand

### P3-01 — Document ingestion and richer desktop observation

- [ ] **Smallest increment:** choose one demonstrated input need, such as local PDF text
  extraction or OCR for a specific inaccessible control. Add it as an isolated adapter;
  region/multi-monitor capture is a separate increment after native capture acceptance.
- **Acceptance/tests:** explicit user-selected input, format/size/page/time limits,
  malformed-document corpus and no external resource fetch; provenance preserved and
  content treated as untrusted. OCR uncertainty is visible and cannot authorize a click;
  sensitive screen regions require review. Measure benefit on the selected workflow.
- **Depends on:** P0-04/06, P1-01/07 for risky parsers, pinned maintained local dependencies.
  **Contracts:** F03/F12. No broad Office/archive ingestion without a concrete need.

### P3-02 — Additional model and server optimization trials

- [ ] **Smallest increment:** one alternative quantization/model or one isolated server
  setting at a time, using existing benchmark/evaluator code and broader task verifiers.
  - [x] A0 feasibility: controlled warm-worker comparison of the existing2048-token
    schema probe versus the configured context, six counterbalanced pairs. Verify actual
    probe/main contexts, identical other payload fields, native load timings/VRAM and
    unchanged microtask results. Do not restart/unload the user's service or apply defaults.
    This request-local experiment needs no new model/store access. Cold conditions and
    matched broad agent-quality qualification remain separate requirements before adoption.
    Verified2026-10-25: all12 actual samples pass, applied contexts and normalized
    payloads match the intended single change. p50 fresh worker excluding warm setup
    8.218s→1.047s;715 default/654 passed/61 skipped,49 targeted passed/one skipped,
    Ruff and wheel/source/import pass. No production default or service mutation.
  - [ ] A1 qualification/adoption: matched broader agent corpus and safety under both
    profiles, controlled model-unloaded comparison with verified ownership, then the
    smallest runtime change only if quality and repeated load/latency gates pass.
    Preserve original output/probe/permission bounds and complete relevant native/runtime
    package regression; no claimed cold or whole-agent result from the A0 microtask.
    - [x] A1a comparison harness: original20 cases/three repetitions per profile,
      eight safety checks per profile, alternating order, source/request/native/context
      receipts and unchanged oracles/permissions. Full136-workflow protocol matrix passes;
      default665 passed/62 skipped, targeted90 passed/3 skipped, Ruff and wheel/source/
      import checks pass. Fixtures do not prove quality. Initial timing failure is retained.
    - [ ] A1b live qualification/adoption: actual-model paired corpus and controlled
      owned model-unloaded conditions, then runtime/package acceptance. Require both
      existing quality/safety gates, no per-case loss and repeated latency benefit.
      - [x] A1b1 actual paired measurement: normal primary service restored; corpus
        9b55fdf021e94b37bf7225e6667a3707 completes, both profiles56/60 and8/8 safety.
        Applied contexts/native/request/source receipts revalidate. All60 latency pairs
        improve, but per-case nonregression fails on download3/3 versus2/3. Candidate
        remains unapplied. All failures and unchanged oracles are retained; no retry-to-pass.
        Evidence: .runtime/p3-02-live-20261026/validation.json. No source/test changes.
      - [ ] A1b2 controlled owned cold/runtime adoption: not accepted; the measured
        candidate failed its prior quality gate, and managed owned model admission
        remains access-denied. Do not replace this with a shared-service unload.
      Retry2026-10-26: application source matches A1a. Python can read the manifest,
      but an owned private-port Ollama0.40.7 service still omits it with Access is denied.
      Admission fails before inference; no live/cold result. Evidence:
      .runtime/probe-qualification-owned/b968ad9d97cc414d9e6984f78079bda2/.
      Owned listener cleanup is verified; fresh MCP acquisition still fails10013.
      Current gate record: .runtime/roadmap-gates/20261026/gates.json. No independent
      SDK/model/native dependency became available on this resume.
- **Acceptance/tests:** matched prompts/order/repeats, cold/warm separation, documented
  actual backend setting, VRAM and p50/p95 end-to-end latency. Preserve task-quality gates
  and restore owned test state; report failures rather than extrapolating from flags.
  Apply defaults only when repeated benefits exceed measurement variability.
- **Depends on:** P1-05/08, ordinary model-store access and user-approved model downloads
  if needed. Never restart/unload another client's service to improve a benchmark.
  **Contract:** F10. Historical isolated cache trials are blocked evidence, not an optimization.

## Execution order and release gates

1. P0-01 establishes current evidence; P0-02/03/04 fix reproduced or source-confirmed defects.
2. P0-05 accepts the native installed product. Its packaging exploration can run alongside
   fixture fixes, but release sign-off requires all applicable P0 checks.
3. Start P1-01 and the single-verifier increment of P1-02. Add P1-04 journaling and P1-08
   evaluation before claiming greater autonomy. Memory, context/UI improvements and optional
   isolation can then be delivered as separate tested increments.
4. Enable only the P2 capabilities with a demonstrated use case and satisfied dependencies.
   Keep P3 optional. No “all features at once” framework migration is proposed.

Each increment needs a reviewed change, denial/failure tests where relevant, its applicable
live check, and a dated update to IMPLEMENTATION.md. A passed source build does not complete
native acceptance; a model report does not complete an independent verifier.

## Current blockers and how to resolve them

Blocked execution2026-10-28 after three consecutive goal-turn occurrences: actual host
Hyper-V group membership/token are absent and the named provider query is still denied.
Guest SSH remains available. No independent incomplete increment passes its existing
prerequisite/benefit gates. Goal is blocked, not complete; preserve all open requirements.
Owner can choose the host management permission procedure or reviewed owner-run commands
in docs/windows-test-vm.md. Verify access after that external change before starting the
isolated execution backend. Evidence:
.runtime/roadmap-gates/20261028-after-p005/blocked-audit-3.json.

Current2026-10-28: P0-05 first/second/third are verified. The clean guest native/upgrade/
retention/uninstall matrix is complete; do not repeat it without relevant changes. Next
P1-07 still needs a managed disposable execution environment and enforceable network/input/
output boundaries. Actual host Get-VM remains denied despite working guest SSH. Model
review/routing/optimization gates retain their measured failures. P3 document/OCR remains
optional without a demonstrated new input need. No other unchecked increment currently
has satisfied prerequisites; no OS isolation or benefit is inferred from transport success.

Historical2026-10-27: after the distinct4B review measurement, three fresh audits confirm unchanged prerequisites:
managed-session VM management remains unavailable, the Windows ISO/owner setup result is
pending, and tested review/routing/optimization benefit gates remain failed. Continuous
execution is blocked, not complete. No remaining requirement is marked done by the audits.
Evidence: .runtime/roadmap-gates/20261027-after-4b-review/audit-3.json. Owner next action:
docs/windows-test-vm.md, followed by the New-VM result and ISO path.

Current2026-10-27: SDK/MCP acquisition, embedding installation/integration and the NSIS
build are resolved; they are not remaining setup steps. P0-05 first/second are complete.
Native independent-Ollama normal-close acceptance now passes; its test fixture and native
window closed after successful owned cleanup. Native capture/preview is now owner-confirmed
with two valid new persisted image attachments; clean install/upgrade/data acceptance remains.
Owner now approves the separate VM and qwen3.5:4b download/evaluation. Candidate is installed;
its full first-attempt evaluation finishes53 passed/5 failed/2 blocked, with eight safety
cases passed. It is not qualified for routing; the9B default stays unchanged.
Hyper-V administrator setup/Windows ISO/guest installation remain prerequisites; no VM
provider has been enabled automatically. See docs/windows-test-vm.md and candidate evidence.
Failed specialist and optimization benefit gates are retained. Evidence:
.runtime/roadmap-gates/20261027-after-native-operator/gates.json and the dated acceptance
records above. The later native evidence supersedes those earlier pending subchecks.

Earlier three post-operator audits recorded unchanged prerequisites and blocked execution:
.runtime/roadmap-gates/20261027-after-native-operator-audit-3/gates.json. Subsequent owner
results close native shared-Ollama/capture checks. Clean installation/upgrade still requires
a disposable Windows test environment; remaining model/VM/benefit gates are separate.

Historical2026-10-26 update after native diagnostics: MCP2.3.0 and its first read-only
provider are verified; SDK acquisition is no longer a blocker. Primary Ollama lists
qwen3.5:9b, while embedding acquisition remains registry10013 despite DNS resolution.
Native diagnostics observe GPU subprocess0xc0000022/unusable GPU; default rendering,
GPU-disabled troubleshooting and an OS-temp profile do not bootstrap in the managed
context. Normal-session native results are required. NSIS/VM/routing and review-benefit
gates remain open. The paired optimization trial remains closed with its failed per-case
gate; no default is adopted. Fresh prerequisite recheck:
.runtime/roadmap-gates/after-native-diag-audit-1/. Earlier unavailable-primary/SDK
statements below are historical. See docs/recovery.md and docs/native-diagnostics.md.

Previous gate audit(2026-10-25, after P3-02 A1a): normal command access has recovered.
No listener exists on11434 and metadata fails with10061; no current model availability
is inferred from earlier successful runs. MCP remains absent with offline/online dry-run
exits1/2 and online socket10013. The isolated embedding cache and NSIS artifact are absent;
no configured disposable VM provider/image is available. Evidence:
.runtime/p3-02-qualification/remaining-gates.json and mcp-*-recheck.txt alongside it.

| Remaining increment | Required next step |
| --- | --- |
| P1-07 isolation | Release-test VM/SSH setup is complete. Supported administrator-backed disposable VM control, a dedicated execution image and denied-network boundary are still needed before implementing/verifying the isolated agent backend. Host provider access remains denied. |
| P2-04 child integration | Both9B and newly measured4B review candidates fail the strict benefit gate. Preserve results and keep delegation inactive; do not integrate without demonstrated benefit. |
| P2-05 routing | Approved4B evaluation is complete but fails the quality gate. Preserve the negative result and keep9B default; routes need a qualified second candidate and paired evidence. |
| P3-02 A1b cold/adoption | Preserve the failed per-case result; do not adopt or retry-to-pass. A separate future candidate needs its own controlled evaluation. Never unload a shared service. |

P3-01 remains optional with no demonstrated new document-input need. No remaining
independent increment currently has all of its external/quality prerequisites satisfied.
Retain incomplete checks; do not infer completion from the A1a protocol harness.

### Public website validation: DNS repaired; managed browser access still denied

1. Normal-session browser acceptance now passes: user-reported 111 tests, 99 passed / 12 skipped
   in 36.246s after the example.com assertion repair. No further DNS repair is required for
   this acceptance gate. Managed-session Playwright remains network-denied independently.
2. If normal browsing also fails at the demo host, have the network/policy owner resolve access. Do not
   disable endpoint protection or add broad origin wildcards.
3. Rerun `./scripts/validate.ps1 -Browser -BrowserChannel msedge`; retain exact failure/pass
   output. Enable `-Model` as well for the combined real-model browser/file workflow.
4. Mark public browsing accepted only when its public-site test passes; passing local
   fixtures already establishes that a browser adapter is implemented.

### Interactive/native acceptance: required environment, not absent source

1. Save unrelated work; use an unlocked standard-user desktop with no concurrent input.
2. Run `./scripts/validate.ps1 -Desktop`, inspect its temporary saved file/readback result,
   and close only the test Notepad window. If it fails, collect the adapter exception and
   Notepad version/window identity; do not attach to unrelated existing documents.
   This Notepad acceptance passed in the user's normal session: 96 passed / 15 skipped,
   48.994s. A repeat is only needed for relevant changes or a new failure.
3. Fully restart via `./desktop-dev.ps1`, then exercise native clipboard/picker/capture/
   export, contextual chat, approvals, cancel, startup/restart and single-instance behavior.
4. Record native evidence separately from `LIVE_STUDIO_UI` browser-harness results. UIA
   inspection/control/screenshots need their own observed checks beyond a typing test.

### Installer: clean-install/upgrade acceptance passed2026-10-28

The actual guest matrix passed; the following is the repeat procedure for relevant changes.
See .runtime/p0-05-vm-acceptance/validation.json and docs/windows-test-vm.md.

1. Use the existing built NSIS artifact and release manifest; build/frozen packaging is
   already verified. Rebuild only for changed application inputs or a demonstrated failure.
2. Use a clean standard-user Windows test environment with the documented runtime/browser/
   external-Python prerequisites. Do not downgrade, uninstall or reset the owner's production
   Studio/history to manufacture a clean environment.
3. Record clean installation, chat and approved real tools, then a tested upgrade preserving
   configuration/history. Observe actual uninstall/data behavior separately from static NSIS
   source inspection. Preserve installer/version/hash and before/after fixture evidence.

### Optional server optimization: historical model-store access denial

1. Use the normal Windows session and existing primary Ollama service; confirm installed
   models are visible. Live inference through that service passed this audit.
2. For isolated trials, let the primary model unload naturally and ensure no active client
   tasks; run `python -m local_agent.evaluate_optimizations` from the project environment.
3. If the isolated service still reports `Access is denied`, retain its bounded diagnostic
   log and ask the machine owner to inspect the specific model-store permission/policy.
   Do not reset ACLs or delete weights blindly.
4. Keep the current working inference configuration until an actual comparison passes.

The original audit identified memory, MCP, scheduling, delegation and checkpoint resume
as engineering gaps. Later increments implemented scoped lexical/semantic text memory,
the pinned read-only MCP provider, read-only scheduling and selected-file checkpoints.
Their earlier acquisition gates are resolved at those bounded verified scopes. Restricted
delegation still lacks a demonstrated benefit; general checkpoint resume is not claimed.
These current gates supersede that audit's earlier no-external-blocker assessment.
