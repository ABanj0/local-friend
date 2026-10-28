# Feature Gap Analysis

F12 native capture/preview verified (2026-10-27): owner confirms the preview appears and
read-only metadata verifies two valid new1600x900 JPEG captures with matching stored sizes.
No raw image export or model-image submission claim. Together with earlier native controls
and lifecycle evidence this resolves the capture validation gap; tested clean-install/
upgrade/history/uninstall remains open. Evidence:
.runtime/p0-05-native-capture-acceptance/validation.json.

F12 independent-Ollama normal-close gap resolved (2026-10-27): actual installed owner run,
saved process/listener/health observations and matching tested-source/package hashes verify
preservation across X close, followed by the harness's separate fixture cleanup. No broader
active-task or hostile-process protection is claimed. Capture/preview and clean-install/
upgrade/history/uninstall remain unverified. Evidence:
.runtime/p0-05-native-shared-model-acceptance/validation.json.

F12 independent-Ollama verification support (2026-10-27): operator check now verifies
separate ownership, unchanged PID/creation time/listener and bounded health across native
normal close, with owner connection/close observations.17 new tests/60 combined checks pass,
zero skips; Ruff passes. This closes the repeatable test-support gap only. Actual exercise
refuses the open Studio, so native preservation remains unverified. Capture has no new
image record yet; capture/preview and install/upgrade/data acceptance remain open. See
docs/native-shared-model-check.md and IMPLEMENTATION.md.

F12 native export verified (2026-10-27): the actual Downloads Markdown file matches all
208 expected UTF-8 bytes from the official two-message export. This verifies delivery,
not merely the UI notice; attachment body omission is intentional. No Save As behavior is
claimed. Capture/preview, native shared-Ollama preservation and tested install/upgrade/data
behavior remain third-increment gaps. Evidence:
.runtime/p0-05-native-export-acceptance/validation.json.

F12 file-picker/attachment verification (2026-10-27): owner confirms the Windows chooser
worked; persisted sanitized fixture text/hash and message binding match, and actual Chat
generation returns the marker. This native subcheck is verified, not a new feature. Full
third acceptance still needs export/download, capture/preview, native shared-Ollama and
tested install/upgrade/data behavior. Evidence:
.runtime/p0-05-native-attachment-acceptance/validation.json.

F12 lifecycle verification completed (2026-10-27): installed native retry budget/backoff,
manual fallback/connection and owned normal-close cleanup now have a passed owner run with
independent report/process/hash validation and a surviving Python fixture. Combined earlier
focus and interruption/no-replay evidence closes P0-05 first. This is a resolved validation
gap, not new application behavior. Third still requires physical dialogs/capture/export,
native shared-Ollama preservation and tested install/upgrade/data behavior. See
.runtime/p0-05-native-lifecycle-acceptance/validation.json and IMPLEMENTATION.md.

F12 retry/fallback prerequisite (2026-10-27): repeatable operator harness is implemented
with twelve new tests and43 combined passing checks, plus rendered recovery1/1. Actual
installed binary identity is verified; the native exercise refuses the still-running owner
instance. Native retry exhaustion/manual fallback remains a validation gap, not a claimed
missing recovery feature or a native pass. No application behavior was modified. See
docs/native-recovery-check.md and IMPLEMENTATION.md.

F12 fresh-review update (2026-10-26): after the pending-approval crash, a distinct Agent
task makes real model calls, requests a fresh review and records denial; the original
interrupted task stays unchanged and the target stays absent. Pre-request history identities
persist. This specific recovery/no-replay/fresh-approval scenario is verified; native retry
exhaustion/manual fallback, physical controls, unrelated-process preservation and tested
upgrade remain gaps. Evidence: .runtime/p0-05-native-recovery-fresh-denial/.

F12 pending-approval interruption update (2026-10-26): native crash changes the captured
waiting task to interrupted, preserves target absence, cleans the old worker and starts
fresh owned services without new task/operation/verifier or approval-resolution records.
The unknown write intent remains explicitly uncertain. This closes the scenario's no-
replay check; fresh resubmission approval, native retry/fallback timing, other active-work
effects, physical controls and upgrade remain separate. Evidence:
.runtime/p0-05-native-pending-crash/validation.json.

F12 idle crash-recovery update (2026-10-26): owner-observed automatic reconnection is
corroborated by the same native PID, fresh owned backend/model chain, retired old children,
single listeners and retained history without new task/operation records. Active-task/no-
replay, native retry timing/exhaustion/manual fallback and generation after this specific
crash remain unverified. Full native/install acceptance stays open. Evidence:
.runtime/p0-05-native-idle-crash-recovery/validation.json.

F12 reopen update (2026-10-26): application-managed backend/model startup and owner-visible
Chat generation work after normal close/reopen. Pre-close conversation/task/message/
verification identities are retained. Exact requested reply wording did not pass; older-
transcript rendering is not explicitly confirmed. Backend crash recovery, active-task/no-
replay, unrelated-process preservation, physical controls and upgrade remain separate gaps.
Evidence: .runtime/p0-05-native-reopen/.

F12 normal-close update (2026-10-26): idle native close releases the recorded native,
PyInstaller pair and owned Ollama processes and both listeners, independently observed
after owner closure. This closes the idle normal-close subcheck; shutdown duration,
unrelated-process preservation in this run, crash/active-work recovery and upgrade remain
unverified. Evidence: .runtime/p0-05-native-normal-shutdown/.

F12 second-launch update (2026-10-26): owner-observed existing-window focus is corroborated
by unchanged native/backend/model PIDs and one backend listener after launch. The narrow
focus/no persistent duplicate check closes; no continuous transient-process trace is
claimed. Native shutdown/recovery, physical capture/export and upgrade remain open.
Evidence: .runtime/p0-05-native-second-instance/observation.json.

## F12 update: installed Agent deny/approve sequence verified (2026-10-26)

The owner completed the actual native file-creation approval sequence. Independent durable
decisions/journal/artifact records confirm denial without an artifact record, then a fresh
approved task with one passed readback matching the independently read18-byte test file.
The narrow native approval gap is closed; second-instance/recovery/shutdown, physical
capture/export and upgrade/history/uninstall remain unverified. Full P0-05 completion is
not claimed. See IMPLEMENTATION.md and .runtime/p0-05-native-approval-verified/.

## F12 update: installed runtime and basic native controls verified (2026-10-26)

Corrected runtime paths are applied; installed Studio owns Ollama, lists both models and
has completed real chat. Installed-backend browser/memory workflows pass independently;
the owner verifies visible reply/Copy/Stop. Raw-vs-installed native hash differences are
now explained/checked through a separate unsigned NSIS tag prediction;9 release/discovery
checks pass. Approval dialogs, native recovery/second-instance/shutdown, physical capture/
export and upgrade/history/uninstall are still acceptance gaps. No full P0-05 completion
or binary-signature/clean-install claim is implied by these narrower verified observations.

## F12 bootstrap gap: installed portable Ollama discovery corrected (2026-10-26)

The owner reproduced executable absence in the installed app despite a working development
runtime. Added trusted executable/model-store paths, standard Windows discovery and a
backed-up operator configuration helper. Existing services and file/model contents remain
preserved. Source/API/config/publication and actual frozen service-start/cleanup tests pass;
an updated NSIS artifact is built. Managed model-store access is independently denied, so
inference and normal-session application of the fix remain unverified. First/third P0-05
native/install acceptance stays open; prior packaging success did not cover this layout.

## F12 update: NSIS packaging verified; installed acceptance pending (2026-10-26)

The missing installer artifact is now present after the owner's normal-session build.
Manifest/source/artifact hashes, deployed sidecar/template and61 frozen modules match.
17 package runtime/socket/live-browser/coding,1 frozen MCP and7 Rust checks pass with
no skips. P0-05 second closes at packaging/helper scope. Native UI/recovery/single-instance,
standard-user install/upgrade and actual uninstall data behavior still lack acceptance;
they are validation gaps, not claims established by the build. Locks are retained and
no security boundary or functioning component was rewritten.

## F05 update: integrated bounded semantic memory qualified (2026-10-26)

P1-03 B is complete at its stated explicit note/text-file scope. Production retrieval after
restart meets fixed32-fact literal/paraphrase gates (32/32 and30/32, keyword paraphrase14/32,
zero cross-project results). Real chat citation, source spans/hashes, changed-file exclusion,
forget/history/vector cleanup and source-chat deletion pass. Source/frozen rendered review
and actual frozen backend workflows are verified in B2a/B2b; no application rewrite followed.
Known Zephyr/Acorn misses and point-in-time freshness limits remain. General document/OCR
ingestion, automatic crawling, native installer verification and OS isolation are separate
capabilities, not hidden claims of this completed increment. See docs/project-memory.md.

## F05 update: file-memory review controls verified (2026-10-26)

P1-03 B2b now provides exact path selection, full excerpt/hash/version review, explicit
import/replacement, saved/stale metadata checks and whole-source forgetting. Source/frozen
rendered tests verify cancellation, preview conflicts, original preservation, blank-chat
source creation and late old-project response rejection. Existing note/semantic/keyboard
flows pass; no backend framework/dependency rewrite is involved. Combined B3 retrieval
qualification remains open, as do native WebView2/installer acceptance and OS isolation.

## F05 update: explicit file-source backend verified (2026-10-26)

P1-03 B2a now provides authenticated reviewed UTF-8 file import, bounded source spans,
raw/normalized hashes and resource/generation tracking. Scope/private-path checks precede
capture; whole-input credential checks precede chunking. Fresh admission detects changed,
missing, unsafe or cache-inconsistent sources, removes vectors and excludes obsolete model
history. Stale snapshots remain visible but cannot be recalled. Forgetting any excerpt or
its source chat removes the complete derived source set without changing original files.
Backup/restore/retention include source metadata with transactional/cascade checks.

836 default tests (765 passed/71 skipped), real source/frozen model restart/change/reimport/
forget workflows, rendered provenance and package source equality verify this backend.
Rendered restore is blocked by an existing Vite listener; its storage contracts pass.
File-selection/review controls B2b and the combined B3 qualification remain missing, rather
than being inferred from the backend. No crawler, cloud fallback, new execution authority,
native-window acceptance or broad quality claim is added. See docs/project-memory.md.

## Native startup verification update (2026-10-26)

The native host creates its window but WebView2 GPU subprocesses fail with0xc0000022
and report an unusable GPU in the managed session. A bounded development diagnostic
now captures that condition without changing rendering/security defaults or exporting
raw logs. Positive/negative/process/HTTP tests and an actual owned diagnostic pass;
the actual application startup observation is a failure, not a native acceptance pass.
P0-05's real UI/single-instance/recovery/installer/upgrade gaps remain open. See
docs/native-diagnostics.md and IMPLEMENTATION.md for the separate diagnostic scope.

## F07 update: first MCP provider verified (2026-10-26)

Typed tools/profiles already existed; the missing read-only local stdio integration is
now implemented and verified. Opt-in `mcp_project_read` exposes one shipped pinned
server behind the same Policy, registry, audit, journal and cancellation boundaries.
Real SDK handshake/list/read, scope/schema/output/time/secret protections, direct server
denials and owned descendant cleanup are tested. An actual local model and actual
frozen server both used the provider; default regression680 passed/64 skipped.

Arbitrary external servers, URLs, remote transports, mutation tools and OS isolation
remain outside this increment. SDK version2.3.0 is installed and pinned; the previous
SDK acquisition blocker is resolved. Offline lock/sync pass for Windows/Python3.12 using
exact SDK-wheel dependency metadata. Other runtime/package targets require independent
resolution and acceptance. See docs/mcp.md and IMPLEMENTATION.md for evidence/limits.

Audit date: 2026-10-22. Evidence and exact verification runs are in
[ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md); implementation increments and gates are
in [ROADMAP.md](ROADMAP.md). No functionality was changed for this assessment.

## Classification

- **Verified:** implementation exists and the named behavior passed an applicable check.
- **Implemented, validation gap:** code exists, but the relevant real environment/path was
  not tested successfully. This is not missing functionality.
- **Partial:** a useful subset works; additional implementation is required.
- **Missing:** no implementation found in source, registered tools, schema, or dependencies.

These labels apply to individual behaviors, not an entire category based on one happy path.
Mock/protocol fixtures establish orchestration contracts, not model intelligence. Browser
acceptance that bridges native IPC does not certify the installed Windows application.

## Capability inventory

| Target | Verified current behavior and evidence | Validation gaps | Missing or partial implementation |
| --- | --- | --- | --- |
| 1. Autonomous planning/execution | `agent.py`, `tools.py`, `test_agent.py`; real read/write and browser/file model workflows passed. Structured plans, sequential actions, budgets, denial handling, empty-response recovery. | No broad long-horizon or adversarial quality result. | Partial: prose plan, no durable step graph, independent completion verifier, or explicit state-based retry policy. |
| 2. Browser / Windows control | Local real Playwright navigation, extraction, harmless fill, click, tabs, download, screenshots, denied POST passed (`test_live.py`). Desktop window identity/Store handoff logic passes unit tests (`test_desktop.py`). | Public browser failed DNS. Notepad type/save/readback, physical screenshots/input/UIA menus, and headed authentication/nested approvals remain unaccepted. | Partial: task-lifetime browser sessions, CSS selectors, no persistent reconciled browser/desktop state. Desktop menus lack a dedicated semantic adapter. |
| 3. Autonomous coding/verification | Scoped files, reviewed overwrites, command profiles, Git staging/review/commit, real failing/fixed unittest cycle (`test_coding.py`); Studio reviewed writes and direct tests/diff passed. | Deterministic bug-fix tests are not autonomous model-generated debugging. User's five addition tests are a single successful run, not a coding quality benchmark. | Partial: no search/repository map, patch transaction/conflict handling, streaming command logs/readiness API, per-project tool environments, or independent task verifier. |
| 4. Long-term memory/retrieval | Persistent conversations, goals, attachments, preferences (`store.py`, store/feature/goal tests). Same-conversation model context passed live. | No semantic retrieval checks exist because retrieval is absent. | Missing semantic/keyword memory service, source indexing, provenance, forgetting/reindexing. Full history replay is partial context management, not retrieval. |
| 5. Durable execution/recovery | Interrupted-task marking, no silent replay, owned worker cancellation (`store.py:233`, manager/runtime tests). | Native GUI crash/EOF cleanup and frozen worker behavior need acceptance. | Missing checkpoint restore/resume; partial consistency, replay, and deadlines. CLI `resume` only clears STOP. Goals retain a checklist, not execution state. |
| 6. MCP/extensible integrations | Static 19-function dispatcher with narrow validation/audit (`tools.py`, safety tests). | No external provider compatibility tests. | Missing MCP client/server integration and versioned typed registry/provider lifecycle. Adding an adapter currently requires editing source. |
| 7. Scheduled/event workflows | Worker progress events/WebSocket updates exist. | No scheduler acceptance tests. | Missing persisted schedules, triggers, queue/leases, timezone/misfire/dedup policies. UI polling is not a workflow scheduler. |
| 8. Specialized delegation | One unified agent selects different tool categories; one active worker protects shared resources. | No delegated workload tests. | Missing parent/child tasks, scoped agent roles, result arbitration, budgets, and cancellation propagation. UI tabs are not delegated agents. |
| 9. Model routing/performance | Manual installed-model selection, context/temperature, local-only transport, GPU/memory status, token/s metrics; live Qwen tool/vision/GPU tests passed. `benchmark.py` and evaluator exist. | No alternatives or broad quality comparison; isolated cache/Flash Attention trials historically failed model access. | Partial: only vision checked at task admission; no tool/schema support matrix, automatic routing, unified max-output/thinking/keep-alive controls, actual prompt budget or compaction. |
| 10. Evaluation/observability | Real tool events, error reports, SQLite task history, hashed audit log, weighted generation metrics; metric/benchmark tests pass. | No measured coverage gate, soak test, hostile-input corpus, native release matrix, or broad agent task success rate. | Partial: no correlated run/step spans, latency breakdown in UI, artifact-linked verifiers, regression thresholds, or redacted diagnostic bundle. |
| 11. OS isolation/permissions | Loopback auth/origin checks, path/origin/command/app scopes, action-specific approvals, environment filtering, Job Object cleanup; default API/safety/process tests pass. | Symlink creation skipped; focus races, hostile code, native app/packaged boundary, and real prompt-injection resistance unproven. | Missing OS filesystem/network sandbox. Partial approval/resource binding and stream redaction; R4/R5 in architecture review. |
| 12. Desktop usability/packaging | Real chat/history/attachments/commands/goals UI scenario passed; TS/Vite/Rust checks pass; debug EXE exists. Development launcher implemented. | Native file dialog/clipboard/capture/export; startup, single-instance, backend crash recovery; packaged sidecar and clean install/upgrade not accepted. | Partial: manual backend restart, large UI component, global activity/preview state, no full backup/restore or paging. Build script exists; release sidecar and installer artifacts are absent. |

## Proposed features and integration contracts

Each item below states the problem, existing foundation, exact gap, expected value,
integration, dependencies/security, and verification. Roadmap IDs define bounded increments;
no item requires replacing the working controller or adding a second inference stack.

### F01 — Reliable task lifecycle and event delivery

Implementation update (2026-10-22): P0-02 first/second increments now verify startup
compensation, atomic terminal outcomes, worker/resource cleanup, storage recovery without
replay, liveness/deadlines and explicit human-wait states. Thirty new fault/transaction tests
and five live Ollama/UI checks pass. P0-02's third increment adds captured high-water
pagination, UI cursor deduplication, acknowledged delivery budgets and explicit RAM-gap
snapshots. Actual socket/SQLite and rendered UI checks verify 5,001 durable events once
through reconnect and backend restart. Approval/preview history stays non-actionable and
tokens are not persisted. The original contract below is retained as audit context; native
crash/restart acceptance and execution checkpoint recovery are still separate requirements.

- **Problem/value:** prevent stuck “Working” states and missing activity after reconnect.
- **Exists/gap:** Manager, pipes, Job Objects, and SQLite work; startup failure, terminal
  writes, event pagination, and hung-worker handling are incomplete (R1–R3).
- **Integration:** compensate startup failures, transact terminal task/message/event state,
  add stable event cursors and a worker readiness/heartbeat/deadline contract. Preserve
  cancellation during blocked model/tool calls and explicit human-wait states.
- **Dependencies/security:** existing SQLite/process code; bounded diagnostics, no raw
  approval persistence, no automatic re-execution. Backend restart must own only its child.
- **Verify:** inject spawn, pipe, database, monitor, and unresponsive-worker failures;
  require a visible terminal outcome, no orphan, and ordered replay of >1,000 events.
  **Roadmap:** P0-02, P0-05, P1-04.

### F02 — State-bound approvals and safer local execution

Implementation update (2026-10-22): both P0-03 increments verify preimage/index/HEAD
review checks, checked atomic/exclusive publication, link/junction defenses and restricted
Git helpers. Actual browser, Windows DACL and model/UI/coding checks pass. The original
contract below remains audit context; optional OS isolation is still P1-07 work, and the
trusted-host race boundary is explicitly documented.

- **Problem/value:** ensure execution still matches the reviewed file/index/destination;
  make trusted host execution distinguishable from isolated execution.
- **Exists/gap:** one-use task approvals and logical scopes exist. Resource digests,
  atomic destinations, complete Git execution-surface policy, and OS isolation do not.
- **Integration:** include precondition digests in reviewed edits/commits; revalidate after
  approval and fail on conflict. Add atomic/exclusive destinations and focused reparse-point
  defenses. Offer a separately configured VM runner for untrusted projects later.
- **Dependencies/security:** stdlib and Git first; VM backend depends on supported Windows
  edition/virtualization and explicit host setup approval. Job Objects remain cleanup,
  not a sandbox. Do not weaken host scopes or let a model grant permissions.
- **Verify:** concurrent file/index/destination changes never execute stale approvals;
  malicious local Git config cannot invoke unreviewed helpers; VM tests cannot read a host
  canary or access forbidden network targets. **Roadmap:** P0-03, P1-07.

### F03 — Safe streaming and attachment context

Implementation update (2026-10-22): P0-04 first increment verifies bounded supported-pattern
redaction across all chunk boundaries before live publication, with aligned stored reports.
Nine new deterministic/real-worker cases and existing real Ollama/UI checks pass. Original
image retention and owned observation cleanup remain the second increment; unknown formats
and pixels are not covered by textual masking.

- **Problem/value:** prevent avoidable live credential display and visual-context loss.
- **Exists/gap:** final text redaction, normalized images, preview consent, ownership checks
  work; chunk-boundary redaction and attachment/observation separation are incomplete.
- **Integration:** use bounded stateful redaction for supported patterns before live events;
  distinguish original attachments from disposable screenshots. Preserve an explicit
  image/text budget and make dropped observations visible.
- **Dependencies/security:** existing attachment/model pipeline; never promise all secrets
  can be detected, never persist image previews or sensitive approval bodies for recovery.
- **Verify:** split synthetic secret patterns at every boundary; test uploaded image plus
  tool screenshot plus follow-up; exercise size limits and crash cleanup without retaining
  sensitive screenshots. **Roadmap:** P0-04, P1-05.

### F04 — Verified coding and outcome-aware autonomy

- **Problem/value:** distinguish a plausible model report from observed task success and
  make multi-file code edits reviewable without clobbering user changes.
- **Exists/gap:** Agent, Git, files, approved tests and bounded failure handling exist;
  independent validators, patch conflicts, repository search, and command log streaming do not.
- **Integration:** verifier results reference real exit codes, expected test counts,
  file hashes/readbacks, and optional browser assertions. Add search under Policy and
  reviewed patch sets using preimage hashes; route command output through existing events.
- **Dependencies/security:** registry/state contracts, stdlib/Git first. Test code remains
  executable code requiring approval. Do not accept “0 tests, exit 0” as verification of
  a requested test suite; do not replay arbitrary commands automatically.
- **Verify:** real model fixes an intentionally broken disposable counter, runs nonzero
  tests, passes assertions, and presents the final diff; false success and conflicting
  edits remain unverified/blocked. **Roadmap:** P0-01, P1-02.

### F05 — Scoped memory and retrieval

- **Problem/value:** recall useful project context across conversations without replaying
  unlimited chat or exposing unrelated files.
- **Exists/gap:** SQLite messages/attachments/goals persist; no searchable memory records,
  source index, embeddings, provenance, expiry, or deletion propagation exist.
- **Integration:** explicit remember/forget and project-scoped SQLite keyword retrieval
  first; then chunk approved text and call local Ollama `/api/embed`. Keep model/dimension,
  content hashes, source spans, timestamps, scope, and consent with each record. Use bounded
  cosine search for a small index; require measured need before adding a vector database.
- **Dependencies/security:** an evaluated local embedding model and inference scheduling;
  no automatic crawl of the user profile, credentials, or every conversation. Retrieved
  instructions remain untrusted data; deletion must remove derived records and vectors.
- **Verify:** cross-session relevant recall with citations; negative cross-project and
  deleted-record tests; stale-source reindex; seeded retrieval recall@5 >=0.90 and no
  scope violations in the acceptance corpus. **Roadmap:** P1-03.

### F06 — Durable steps and safe checkpoint resume

- **Problem/value:** recover useful progress after a crash without repeating mutations.
- **Exists/gap:** task history/interrupted marking and user-reviewed goals exist; no
  persisted continuation or resumable executor exists. P1-04 now adds Studio effect
  classification, durable intent/result boundaries, interrupted/unknown reconciliation
  and read-only artifact inspection; historical rows have no reconstructed journal.
- **Integration:** journal named steps, tool intent/result and artifact preconditions in
  Store. First offer inspect/reconcile/start-new-run from recorded context. Later checkpoint
  a clearly supported read-only/idempotent subset; keep non-recoverable desktop/browser
  actions interrupted and require a fresh observation/approval.
- **Dependencies/security:** F01/F02/F04 and versioned registry; approval expiry and input
  changes invalidate continuations. Never claim exactly-once external effects or serialize
  a live browser/UI handle as a durable checkpoint.
- **Verify:** crash before execution, after effect but before commit, and after commit;
  reconcile unknown outcomes and perform zero blind repeated side effects. Only supported
  steps can pause/resume across restart. **Roadmap:** P1-04, P2-01.

### F07 — Typed tools and MCP integration

- **Problem/value:** extend capabilities without bypassing the established safety boundary.
- **Exists/gap:** static validated dispatcher exists; versioned provider interfaces,
  permission profiles and MCP clients do not.
- **Integration:** introduce ToolSpec metadata while wrapping existing adapters. Add a
  namespaced MCP provider behind the same Policy, approval, audit, timeout, and result
  normalization interfaces. Begin with a pinned, explicitly configured read-only local
  stdio server; no arbitrary model-supplied server executable or URL.
- **Dependencies/security:** compatible pinned official MCP SDK/protocol; owned process
  lifecycle, output limits, deny unknown schemas/capabilities, no inherited secrets. Server
  descriptions/content are untrusted; MCP does not supply OS isolation automatically.
- **Verify:** existing tool tests remain unchanged in behavior; a real test server lists
  and reads only approved data; schema changes, out-of-scope requests, disconnects,
  cancellation, and attempts to launch unapproved servers fail closed.
  **Roadmap:** P1-01, P2-02.

P2-02 dependency audit(2026-10-25): P1-01's versioned immutable ToolSpec/profiles already
exist; the missing part is the MCP adapter/provider integration. Official mcp2.3.0 is a
candidate compatible with the host's Python version, but SDK/transitive/runtime behavior
is unverified. It is absent from the local cache; normal PyPI dry-run fails socket10013.
No application package or tool behavior changed and no handshake was simulated as proof.
P2-02 remains open pending ordinary dependency access and real protocol/policy tests.
See IMPLEMENTATION.md and .runtime/p2-02-mcp/acquisition.json.

### F08 — Scheduled and event-driven workflows

- **Problem/value:** run repeatable approved local work without retyping objectives.
- **Exists/gap:** interactive task execution and events exist, but schedules, durable queue,
  trigger identity, misfire/coalescing, and execution leases are absent.
- **A0 update (2026-10-25):** schema6 now supplies bounded private trigger deduplication,
  owned expiring admission claims and atomic queue/task/checkpoint association. Concurrent
  callers, actual crashes and lost commit acknowledgements cannot consume a trigger twice.
  This is retained admission, not exactly-once execution.97 targeted and48 packaged
  regressions pass;574 default passed/59 skipped. No timer, dispatcher, API or scheduling
  UI exists yet; A1 interval policy/lifecycle and B directory triggers remain missing.
  Evidence: .runtime/p2-03-queue/validation.json; guide: docs/workflow-queue.md.
- **A1 update (2026-10-25):** schema7 now persists interval slots and explicit UTC
  skip/latest-slot coalescing, display zones, disable and emergency-stop pause. The owned
  runtime timer uses bounded metadata preflight and normal read-only inspection workers,
  exact queue/schedule binding and restore drain.597 default passed/60 skipped;131 targeted
  and52 packaged checks pass without skips;30 archived code entries match source.
  A/A1 close. Directory triggers/debounce/self-output suppression (B) remain missing;
  always-on services and recurring mutations are outside the implemented scope.
  Evidence: .runtime/p2-03-interval/validation.json; guide: docs/interval-inspections.md.
- **B0 update (2026-10-25):** bounded private directory observations now provide stable
  identity/content fingerprints with explicit incompleteness and credential/link/state/
  known-output exclusions.14 new real-filesystem cases pass without skips;611 default
  passed/60 skipped;53 targeted passed/one legacy symlink skip. Existing activated
  runtime/frontend and binary are unchanged. This source-only prerequisite does not
  establish a directory-trigger workflow: durable baseline/debounce/IDs, owned observation
  execution and API/UI dispatch/disable/stop remain B1. See docs/directory-observations.md
  and .runtime/p2-03-directory-snapshot/validation.json.
- **B1 update (2026-10-25):** schema8 persists scoped directory baselines, debounce
  candidates, generations and exact queue/source bindings. The existing serial scheduler
  owns bounded observation/model children and normal read-only inspection admission.
  Authenticated UI/API controls, disable, shared persisted pause, restart/crash deduplication,
  restore and retention are verified:638 default passed/61 skipped,172 targeted and56
  packaged checks without skips;33 archived entries match source. A full-run counterexample
  reopened B0: late names can escape unchanged directory stat signatures. A second bounded
  filename enumeration and timestamp-restored regression fix that gap. B0/B1/B now close
  for selected-file Studio-only inspections. Matching polls are not continuous stability,
  atomic snapshots or between-poll event capture. See docs/directory-inspections.md and
  .runtime/p2-03-directory-workflow/validation.json. Real-model/native gates remain separate.
- **Integration:** persist schedule/trigger records in SQLite and enqueue normal tasks
  through the coordinator. Start with one read-only interval workflow while Studio is
  running; then approved-directory file changes with debounce and event deduplication.
- **Dependencies/security:** durable state, explicit permission profiles and resource
  leases. No unattended blanket approval; mutations await an actual user or expire. An
  always-on service is a separate deployment decision, not implied by a desktop timer.
- **Verify:** DST/timezone, restart/missed-fire policy, duplicate notifications, own-output
  loops, task conflicts, and approval timeout. Disabled schedules launch nothing.
  **Roadmap:** P2-03.

### F09 — Bounded specialized delegation

- **Problem/value:** separate review/research responsibilities when evaluation demonstrates
  an advantage over one controller.
- **Exists/gap:** one unified controller/worker exists; no parent-child task contract,
  restricted role grants, result verification, or inherited budgets exist.
- **Integration:** parent coordinator creates one read-only review child first, with its
  own scope and evidence artifacts. Keep parent responsible for edits and final results;
  serialize GPU/desktop ownership. Consider concurrent independent reads only afterward.
- **Dependencies/security:** typed tools, durable parent/child state, cancellation/resource
  leases, evaluation suite. Child grants are a subset of parent grants; no recursive or
  unbounded spawning and no approval laundering through child output.
- **Verify:** child cannot mutate/escalate; parent stop kills owned descendants; tool/token
  budgets hold; quality improves on the same seeded tasks versus a single agent.
  **Roadmap:** P2-04.

### F10 — Model capability profiles and measured routing

- **Problem/value:** avoid unsupported tool/image requests, context failures, and tuning
  that improves speed while degrading actual task outcomes.
- **Exists/gap:** installed-model picker, vision check, usage metrics and benchmark harness
  exist. No general capability/quality routing; production output is mostly fixed at 2048,
  thinking disabled, keep-alive five minutes; context uses character heuristics.
- **Integration:** centralize generation options and probe tool/schema/vision capabilities.
  Add output reserve, truncation/finish-reason reporting, bounded user-reviewed compaction,
  and prompt/load/first-token metrics. Later route by explicit local task profiles and
  measured quality, with user overrides and serialized model loads.
- **Dependencies/security:** actual installed models and versioned evaluation artifacts;
  no cloud fallback, surprise downloads, permanent global server changes, or silent
  semantic change during a task. Stop on unsupported requests rather than dropping images.
- **Verify:** request payloads reflect settings in every mode; model switches invalidate
  capability caches; context boundary/truncated outputs fail visibly; paired benchmarks
  preserve quality thresholds and show latency/memory differences. **Roadmap:** P1-05, P2-05, P3-02.

### F11 — Evaluation, diagnostics and maintainable evidence

- **Problem/value:** detect regressions and make capability claims reproducible.
- **Exists/gap:** 88 distinct test implementations, live flags, synthetic microbenchmarks,
  events and audit hashes exist. Duplicated discovery, stale acceptance prose, no broad
  quality/latency/security gate, limited correlation and discarded stderr remain.
- **Integration:** separate fixture/live/native/release suites and machine-readable results;
  attach run/step/tool IDs, timings, verifier artifacts and redacted diagnostics. Reuse
  benchmark helpers; report model/config/hardware, failure taxonomy and sample size.
- **Dependencies/security:** existing unittest/Playwright and monotonic timing; no hosted
  telemetry required. Minimize stored prompt/tool content, test redaction and retention,
  and keep deterministic tests separate from model-quality scores.
- **Verify:** all enabled suites have explicit outcomes; seeded coding/browser/failure/
  injection tasks have observed oracles, latency distributions and reproducible artifacts;
  unknown/failed verification cannot be counted as success. **Roadmap:** P0-01, P0-05, P1-08.

### F12 — Accepted Windows product and usable history

- **Problem/value:** deliver the integrated app without terminal management or hidden
  dependency failures, and make lengthy sessions manageable.
- **Exists/gap:** development launcher, native lifecycle source, debug binary, sidebar,
  attachments, goals and approval UI work in bounded tests. Release installer/native
  acceptance, diagnostic UX, task-scoped history, accessibility and backup/restore are open.
- **Integration:** finish existing PyInstaller/Tauri NSIS pipeline, explicit dependency
  preflight, native lifecycle tests and bounded restart. Extract UI components behind typed
  events; scope previews to tasks, page history, and add SQLite online backup/restore.
- **Dependencies/security:** MSVC/WebView2/NSIS packaging tools, correct browser runtime,
  external Python for coding profiles. Preserve config/data on upgrades; no broad native
  filesystem/shell capability, unrelated process termination, or automatic task replay.
- **Verify:** clean standard-user install/launch/chat/tool approval/worker spawn; offline
  startup diagnosis, single instance, backend crash, shutdown, restart, upgrade and
  uninstall/data-retention behavior; keyboard/focus/900px viewport checks and consistent
  backup restore. **Roadmap:** P0-05, P1-06. Optional document/OCR support: P3-01.

## What should not be rebuilt

P1-06 A update (2026-10-24): integrated chat/model/workspace/history/activity/approval
components and validated unknown event contracts now scope activity/output/previews to
the selected conversation/task, with globally identified approvals and stop retained.
All 33 frozen UI/runtime/socket/loop checks passed, alongside 18 Node checks, TS/Vite,
Ruff and default 456 passed / 51 skipped. Real Edge previews and approved file/test
actions are exercised; UI model/native IPC remain fixtures. Server-only Windows Selector
loop corrects the observed shutdown reset without changing worker policy (512-socket
limit). A is verified; F12 still lacks B paging/accessibility/drawer/backup/retention and
native install acceptance. Current actual-model manifest access is a separate open gate.

P1-06 B1 update (2026-10-24): dialog focus containment/return, keyboard navigation, safe
Escape and900px activity access are now verified by all34 frozen rendered/runtime checks
and a separate actual Edge keyboard/visual scenario. Direct emergency stop and explicit
approval are preserved even with stacked modals. Default456 passed /52 skipped, TS/Vite,
18 Node checks and Ruff pass. F12 still lacks bounded history paging, backup/restore,
configured retention and native installed-product acceptance; B remains open.

P1-06 B2a update (2026-10-24): authenticated history pages and index-only migration4 are
verified independently (30 source targeted,35 frozen checks; default468 passed /52 skipped,
Ruff,18 frozen code/source matches). Pages cover conversations, scoped visible messages
and task metadata with strict scope-bound cursors and default50/max100 rows. Legacy
routes/model context are preserved. Desktop paging is still missing; B2b must integrate
controls, selection/replay and export behavior before B2 closes. No byte-bound/snapshot,
model quality, native install, backup/retention or isolation claim.

P1-06 B2b conversation update (2026-10-24): fifty-row sidebar, older navigation, stored
title search, stale-response rejection and selected metadata are verified on72 actual
chats, including rename/new/delete/reload. All36 frozen checks, source history12, TS/Vite,
18 Node checks and Ruff pass; default469 passed /53 skipped. Metadata lookup is minimal
and authenticated. Message/task paging and export completeness remain missing; B2b/B2
are open. No actual-model, native-install or backup/retention claim follows from UI tests.

P1-06 B2b Task-history update(2026-10-24):50-row windows, metadata-only global activity
including retained owned slots, older selection/reconnect and stale deletion handling are
verified beyond200 runs. Actual251-run UI keeps approvals/stop global while navigating;
default477 passed/55 skipped,38 packaged checks plus final3 affected UI cases pass,
TS/Vite/19 Node/Ruff and19 sidecar code matches. Message paging/complete bounded export
are implemented and protocol-verified, rather than missing, but their actual-model UI gate
remains blocked. B2b/B2 remain open. Full backup/validated restore and retention were
still missing at this task-history boundary; the backup component is updated below.

P1-06 B3a update(2026-10-24): confirmed fixed-destination online snapshots are implemented
and verified, including private binary attachments, all nonempty stored tables, committed/
uncommitted WAL distinctions, active-owner refusal and exclusive publication. Final39
source targeted, source UI1 and39 packaged checks pass; default488 passed/56 skipped,
TS/Vite/19 Node/Ruff and20 sidecar source matches. Backup is no longer missing; staged
validated restore/rollback/restart and retention still are. No encryption, project-file,
checkpoint-resume, real-model or native-install claim. B3a closes; B3 remains open.

P1-06 B3b1 update(2026-10-24): restore preparation is now implemented and verified. It
checks an exact app-owned backup ID/hash and reviewed schema, preserves every nonempty
required table in fresh state, renews only store identity, saves current rollback data,
and writes readiness last. Actual crash/failure/ownership/hostile-schema/source-swap
negatives and real HTTP/restart pass. Final54 targeted/18 packaged checks, default503
passed/56 skipped, Ruff and21 sidecar source matches; frontend remains unchanged.
Activation/current-state routing/restart/rollback UX remains missing B3b2. Drafts never
activate on ordinary restart, so this does not complete B3b or B3. Retention stays open.

P1-06 B3b2 update(2026-10-24): confirmed activation and rollback now work through fixed
generation routing, current-state snapshots, request drain, state ownership and backend
restart. Actual before/after publication crashes preserve original data; no tool replay,
blind undo or empty-store fallback. Selected-state worker approval/artifact persistence,
stale cursor reset and900px UI recovery with held old responses are verified. Final default
527 passed/57 skipped,79 targeted plus worker1,43 packaged checks, TS/Vite/19 Node/Ruff
and24 archived code matches. B3b2/B3b/B3 close. Retention remains missing B4; native IPC/
inference are fixtures in rendered tests, so installed-product/model gates remain open.

P1-06 B4 update(2026-10-25): manual conversation retention is now implemented and verified.
Saved age/recent/batch policy, exact-content bounded previews, explicit confirmation and
atomic dependent-record cascades reuse the existing store/memory boundaries. Selected,
recent, unfinished, pending and active work is protected; source-memory deletion resets
future kept-chat context without removing visible transcripts. Project/backup/generation
files remain. Stale/expired/replayed reviews, limits, rollback, real restart and900px
keyboard/delayed-preview/owned-approval refusal pass. Final default540 passed/58 skipped,
all90 targeted and45 packaged checks, TS/Vite/19 Node/Ruff and25 code matches. B4 closes;
B2b/B2/B actual-model UI and native installed-product gates remain open. No scheduled
cleanup or secure erasure. See docs/studio-retention.md and IMPLEMENTATION.md.

P1-03 A recovery update (2026-10-24): independently reusing the existing local service
now passes the actual restart/recall/citation/forget case (1/1,zero skips,3.417s). Combined
with current32/32 scoped keyword recall, provenance/deletion/authority checks and frozen
memory UI flows, explicit-memory A is complete. Original owned-startup manifest-denial
logs remain unexplained; no service/model/ACL change or semantic retrieval claim. B's
embedding evaluation, chunk/version tracking and index invalidation remain incomplete.

Reuse the local Ollama transport, deterministic adapters, shared policy, process supervisor,
SQLite ownership model, and real UI flows. Missing memory, scheduling, MCP and delegation
are new modules, not reasons to replace these components. A broader agent framework or
second autonomous editor should be adopted only after a concrete integration demonstrates
better measured outcomes without weakening approvals, locality, cancellation or verification.


### P0-04 image-context verification update (2026-10-22)

R6 / F03: original image eviction is fixed. Agent retains user images and only evicts
prior transient observations; total image count is eight, each new observation is at
most 1600 pixels per side / 2 MiB. Owned capture registry/leases support safe preview,
consumption, cancellation and abandoned-run cleanup without deleting chat attachments
or unregistered files. Twenty targeted lifecycle/image/startup checks and two actual
Ollama + Edge tests pass, including spawned Studio preview/attachment preservation.
See IMPLEMENTATION.md for complete regression evidence and initial service failure.
These checks do not establish physical desktop capture, native packaging, pixel-secret
redaction or OS isolation. Unknown/replaced owned paths deliberately block cleanup.


### P0-05 packaging evidence update (2026-10-22)

The actual PyInstaller sidecar and optimized Windows release now build. Final frozen
acceptance passes 15 runtime, authenticated socket, approved external-Python and actual
Ollama/Edge browser/screenshot tests. Exclusive first-run configuration publication has
three native tests; seven Rust tests pass overall. Default regression: 197 passed /
26 skipped. Artifact checksums and 47 source/lock input hashes were independently checked
against `dist/release-manifest.json`. This closes frozen-path validation gaps at that scope.

Native single-instance/crash acceptance remains open after WebView2 resource-in-use;
NSIS bundling is externally blocked by socket error 10013 downloading the official tools.
No installer, clean install or upgrade pass is claimed. P0-05 stays unchecked; the next
independent increment is P1-01, depending on completed P0-03. See IMPLEMENTATION.md and
docs/desktop.md for commands, exact evidence and blocker-resolution steps.


### P1-01 contract verification update (2026-10-23)

Versioned built-in ToolSpec records and per-run Unified/Coding/Browser/Desktop profiles
are implemented. Registry/profile metadata is immutable; schema/type/default/command
validation precedes adapter dispatch. The CLI, authenticated task/slash API and rendered
UI preserve the profile, including original-profile regeneration and legacy task migration.
All 19 final model-facing schemas match the saved pre-increment implementation exactly.
Fourteen targeted cases, four real UI/approved-test/local-browser checks and final default
regression (211 passed / 27 skipped) pass; TypeScript/Vite, Node and Ruff pass.

This verifies the registry/profile contract in F07. MCP/provider integration remains open.
Live model regression is currently blocked: the managed Ollama service cannot open its
Qwen manifest. Tests were attempted and failed, not counted as passes; historical 2026-10-22
model evidence is not described as current. Native/NSIS blockers also remain. See the latest
IMPLEMENTATION.md entry and docs/tool-profiles.md for exact evidence and resolution steps.
Next: P1-02's first configured-test verifier, using the tested registry/worker boundary.


### P1-02 first verifier evidence update (2026-10-23)

F04 now has separately persisted configured-unittest observations: TestResult counts,
exit code, canonical status and command hash. Structured counts distinguish nonzero passes,
zero discovery, skips, expected failures and unsupported/missing results. Model/console
prose cannot create records. Exact execution still requires approval; changed reviewed
helpers are rejected. Fresh bytecode-cache scope prevents same-tick stale imports.

Evidence/event persistence is atomic and idempotent; API retrieval is authenticated;
records survive interruption and are removed with conversations. UI describes an observed
run, separately from reported task prose. Eighteen verifier checks pass; default regression
229 passed / 27 skipped; actual rendered approval/test/evidence UI and five rebuilt frozen
backend checks pass. See IMPLEMENTATION.md and docs/test-verification.md for exact limits.

P1-02 A remains open for artifact readback/hash and current real-model counter acceptance.
The helper is trusted-host execution, not hostile-code attestation or an OS sandbox. A hard
crash can leave small helper/count metadata. Existing model/native/NSIS blockers remain;
no skipped/blocked gate is counted as passed. Next: the artifact verifier within A.


### P1-02 artifact evidence update (2026-10-23)

Coding writes and literal no-ops now have bounded exact-byte/SHA-256 readback observations.
Strict path/link and reviewed-resource checks remain; changed or missing publications are
recorded without retry/repair. Parent validation independently determines the verdict.
Metadata and resource-version digests persist via the existing verifier transaction/API,
without raw file contents or errors. UI distinguishes artifact readback from test results.
The previous newline-normalized no-op comparison was fixed so CRLF/LF changes are reviewed.

Thirteen artifact and eighteen test-verifier cases pass; default 242 passed / 28 skipped;
two rendered scenarios and three rebuilt frozen-backend/UI checks pass. TS/Vite/Node and
Ruff pass. P1-02 A's initial components are implemented; full A stays open for current
model-driven counter acceptance. Live model/native/NSIS blockers remain unpassed. This is
point-in-time byte evidence, not semantic task correctness or future-state authorization.
Next independent work: scoped repository search within P1-02 B. See IMPLEMENTATION.md and
docs/artifact-verification.md for exact evidence and limits.

### F04 scoped search increment (2026-10-23)

Bounded literal repository search is now implemented and verified through the Coding/
Unified tool, authenticated API, real spawned worker and rendered Workspace search/file
viewer. Results include exact source locations, observed hashes, sanitized previews and
explicit incomplete coverage. Credentials/state/links and noneligible text are excluded;
this is not semantic retrieval or an atomic repository snapshot. No extra dependency.

Evidence: 17 search cases plus 14 contract cases pass; full default 259 passed / 29 skipped,
three rendered UI scenarios and seven rebuilt frozen/runtime/UI checks pass. TS/Vite/Node/
Ruff pass. UI model protocol fixtures do not establish inference quality. Current real-model
acceptance remains blocked (port 11434 connection refused). Native/install gates stay open.
P1-02 B remains partial: reviewed patch sets with preimage conflicts are next; bounded
command streaming and background readiness still require implementation and verification.

### F04 reviewed patch-set increment (2026-10-23)

Related create/replace sets now share one diff/hash review, raw-byte preconditions and
whole-set checks before mutation. Pending preimages revalidate during sequential publication;
individual readbacks are durable artifact observations. Conflict/denial and failure/stop
tests establish the stated guarantees, including incomplete outcomes without blind replay
or rollback. The existing rendered approval UI displays both proposed files and both
observations. Three actual worker scenarios include separately approved real unittest execution.

Evidence: 17 new patch cases, 91 targeted checks, default 276 passed / 30 skipped, four
rendered scenarios and eight rebuilt frozen/backend/runtime checks pass; TS/Vite/Node/Ruff
pass. No new model-quality/native/install pass. This supports bounded UTF-8 create/replace,
not deletion/rename, cross-file crash atomicity, OS isolation or durable reconciliation.
P1-02 B stays partial: bounded command streaming and background readiness remain next.

### F04 bounded foreground output increment (2026-10-23)

Approved foreground command/test output now streams before exit through redaction, bounded
durable deltas and the existing authenticated replay mechanism. UI shows latest-three
commands scoped to the selected conversation, safe partial output after cancellation,
truncation/retention warnings and unknown interrupted outcomes. Structured test counts stay
independent. Host-only bounded raw Git parsing preserves policy inspection/fingerprints;
raw output cannot stream. All 21 tool schemas are unchanged.

Evidence: 15 stream tests and 83 targeted checks pass; final default 291 passed / 32 skipped;
six rendered scenarios and ten rebuilt frozen/backend/UI/runtime checks pass, as do TS/Vite,
ten Node tests and Ruff. Actual Windows owned-child exit and unrelated-process survival
are tested; no OS isolation or native WebView/model-quality claim. P1-02 B remains partial
for background output/readiness. Live model listener is absent; native/install gates remain.

### F04 owned background readiness increment (2026-10-23)

Bounded background output/status and optional approved loopback readiness are now implemented
and verified through real owned servers/processes, HTTP probes, Worker/Manager persistence
and the rendered UI. command_status cannot target another process or arbitrary URL. Ownership
ambiguity and failed readiness fail closed; known-pattern redaction, exact status and a
total probe watchdog cover output and slow/trickling responses. Normal completion/cancellation
tests prove owned server/test cleanup. Readiness remains timestamped observation, not correctness.

Evidence: 20 new background cases, 58 targeted checks, default 311 passed / 34 skipped, eight
rendered scenarios and twelve final rebuilt frozen/backend/UI/runtime checks pass; TS/Vite,
eleven Node and Ruff pass. P1-02's initial engineering components are present, but full A/B
acceptance remains open for current real-model coding verification. Services remain task-owned;
no checkpoint/daemon/OS-isolation/native-install claim. Next safe independent work is P1-08 A,
whose dependency is explicitly the completed verifier components, while broader P1-02 gates
remain blocked. Fresh primary model probe: no listener; native/NSIS gates unchanged.

### F11 instrumentation/export increment (2026-10-23)

Studio run/decision/tool/approval correlation, fixed outcome taxonomy, worker latency
breakdown and content-free diagnostic export are implemented and verified. Reuses task IDs,
events, verifier references and native final metrics. Timing distinguishes nested waits;
partial/legacy/interrupted data has no invented durations or task certificate. The bounded
authenticated snapshot/export omits prompts/content/paths/model names and exact credentials.

Evidence: 17 new cases, 70 targeted checks, default 328 passed / 35 skipped, nine rendered
scenarios and thirteen final frozen/backend/UI/runtime checks; TS/Vite/eleven Node/Ruff pass.
Standalone CLI trace coverage, operation journaling, p50/p95 corpus aggregates and repeated
real-model quality remain unimplemented/unverified as applicable. P1-08 A is complete at
its stated Studio contract; B's versioned corpus/runner is next. Model/native/install gates
stay open; protocol fixtures establish integration, not inference quality.

### F11 corpus/oracle contract component (2026-10-23)

P1-08 B now has twenty versioned model task definitions and eight separate deterministic
safety definitions, read-only state/tool/browser oracles and strict report aggregation.
Sixty model repetitions and eight safety observations are required by the contract;
missing/blocked/inconclusive data cannot establish a complete model success rate. Mixed
identities/duplicates fail closed. Native metrics, all-outcome p50/p95, sample/failure
coverage and the safety gate remain separate. No model prose/content/credentials export.

Twenty component tests pass with the real local-browser denial enabled; seven other
denials use actual Tools. Default 347 passed / 36 skipped, Ruff and real wheel/data/load
checks pass. These results establish the contract, not a measured model score or semantic
code correctness: Python oracles compare ASTs without execution. The CLI does not yet run
tasks or attest submitted observations. Next: owned fixture/workflow adapter, bounds and
real metadata/usage collection, then three actual model repetitions. Latest localhost tags
probe timed out. B and broader model/native/install gates remain open.

### F11 actual runner and measured corpus gate (2026-10-23)

The production Agent/Tools runner is implemented and verified with disposable scopes,
loopback fixtures, exact grants, guards, bounded owned-process cleanup, pinned metadata
and native usage. Source tests: 366 passed / 37 skipped; final target 41 passed / 2 skipped;
Ruff and real packaged-wheel/load checks pass. The explicit protocol matrix passes all
60 workflows/8 safety cases; this remains separate from inference quality.

Actual unchanged-corpus Qwen run: 55/60 (91.7%), all eight safety cases, zero observed critical
effects, complete metrics; weighted 67.38 tokens/s, task p50/p95 7.328/12.328s. Five failures
remain, including exact-newline loss and three tool-error causes not yet proven. Their
workspaces and a sanitized baseline/regressions are retained; no oracle was relaxed.
P1-08 B's declared gate is met at this narrow scope, not universal autonomous reliability.

Five other real-model checks pass. Functional counter debugging is observed, but its legacy
test profile bypasses structured count instrumentation and yields an inconclusive verdict.
Next increment must align that acceptance fixture before closing P1-02 A/B. Native/install,
durable journals/checkpoints, memory and OS isolation remain separate outstanding work.

### F04 counted real-model acceptance closure (2026-10-23)

The legacy `-B` fixture gap is fixed without changing production command recognition.
Canonical execution now requires trusted actual helper/code/path/nonce/cwd approval and
machine count records. Observed Qwen workflow: initial 3 tests/1 failure, then 8 passing
tests, independent counted 8 passing and separate oracle 6 passing, with original tests
preserved and Git diff reviewed. False stdout/model success and unsupported/missing/zero/
skipped counts cannot satisfy it. LF/CRLF trusted encodings do not permit arbitrary code.

Four new cases, 28 targeted passed / 1 skipped, default 370 passed / 37 skipped and Ruff
pass; actual live opt-in passes with no skip. P1-02 A/B's engineering and model acceptance
are satisfied at the documented scopes. Next dependent increment is P1-04. Broader model
reliability, data-version freshness, durable execution and native/install acceptance remain
separate; the five P1-08 baseline failures are retained unchanged.

### F06 observation/reconciliation increment (2026-10-23)

P1-04 now supplies Studio numbered migrations, decision/tool intent/result rows, effect
classes and bounded artifact preconditions. Committed parent acknowledgements gate
dispatch and continuation. Terminal/restart handling preserves completed results and
marks missing observational results interrupted or uncertain effects unknown, with zero
replay. Seven migration cases preserve old data/identity/cursors and test refusal/rollback.

History inspection compares current files within the currently approved project; it
neither authorizes an action nor certifies unknown outcomes. A fresh-instruction action
opens the composer with no submission or approval reuse. Real spawned-worker crashes
cover all four required boundaries; source/frozen rendered checks cover completed and
restored-unknown UI. Final default: 399 passed / 40 skipped; targeted: 71 passed / 1
skipped; actual Qwen Studio write/read acceptance: 1 passed, no skip; final frozen UI/socket:
11 passed, no skips. TypeScript/Vite/Node/Ruff pass; evidence in IMPLEMENTATION.md.

Remaining F06 work is durable continuation and supported checkpoint/resume (P2-01),
effect-specific external-state reconciliation and CLI journal integration. No exactly-once
effects, restored live handles, automatic rollback or OS-isolation claim. Native/install
acceptance stays independent. Next actionable dependency is P1-05 A.

P2-01 update(2026-10-25): one selected-file read-only inspection workflow now supports
durable completed-step checkpoints, deferred pause and explicit linked-task resume across
worker/backend restart. Scope/file identity/content, model/version/options, memory epoch
and store identity are rechecked; unsupported histories refuse continuation. Only selected
file reads are exposed. Transcript validation excludes approvals/hidden reasoning/handles,
and independent file coverage prevents a model-only completion claim. Actual commit/crash/
restart and permission/cascade negatives pass. Final default561 passed/59 skipped; all48
packaged,130 targeted plus late32/2 and source rendered1 pass; TS/Vite/19 Node/Ruff and26
code matches. P2-01 closes at this subset. General-task resume, external-state reconciliation,
CLI integration, actual-model quality and native installed-product acceptance remain open.
Inference/native IPC are explicit fixtures in the rendered checks. See IMPLEMENTATION.md
and docs/inspection-checkpoints.md.

### F10 validated options/admission increment (2026-10-23)

P1-05 A is implemented and verified: shared strict options/payloads, user-controlled output,
thinking/residency, local identity/version/TTL capability cache and an actual bounded schema
probe. Unsupported tools/images/thinking and remote models fail admission; images are not
dropped. Length/unknown/missing-final responses cannot authorize tools or task success.
Partial chat survives through safe redaction. Metrics distinguish native prompt/load data,
first generated token and visible content; non-streaming arrival is unknown. Reasoning text
is not exported by timing instrumentation, and probe cost is explicitly separate.

Final evidence: 421 default tests passed / 42 skipped, five actual Qwen checks passed,
22 final frozen UI/runtime/socket checks passed, and TypeScript/Vite/Node/Ruff passed.
Named model controls and incompatible/stale metadata are fixture tested; no alternative
model or paired performance improvement is claimed. Existing model baseline failures
remain preserved. Exact prompt/schema/image/output reserve, bounded compaction and seeded
original-versus-compacted comparisons remain P1-05 B; routing stays later roadmap work.

### F10 estimated budget/compaction increment (2026-10-23)

P1-05 B is verified: full output/schema/text/template/image estimates, bounded extractive
receipts, preserved instructions/originals/call groups and canonical evidence references.
Protected context cannot be silently removed; native truncation/shift are disabled on the
verified Ollama API, and estimate/native overflow blocks. Conversation-scoped numeric
notices explain the last request without storing prompts/excerpts/paths in those notices.

Final evidence: 439 default tests passed / 47 skipped; 24 frozen UI/runtime/socket checks;
four final actual-model tests including all six original/compacted semantic variants,
native rejection, real Studio compaction and independent counted coding verification;
two original-image regressions, source UI and build/lint/Node checks. Early uncompacted
literal-key baseline failures remain documented; field mapping was clarified equally,
with exact oracles retained and a negative case rejecting the erroneous proposal.

Missing work now includes exact model-specific tokenization where a stable interface
becomes available, general long-term memory/semantic retrieval, routing and broader
adversarial/long-horizon quality evidence. Excerpts are not lossless or completion proof.
Existing corpus failures and native/install/OS-isolation gaps remain. P1-03 A is next.

### F05 explicit-memory implementation and current gate (2026-10-24)

Explicit note/message-snapshot remember/search/confirmed-forget now exists in schema v3,
authenticated API, worker context and Studio. Scoped source IDs/hashes, source-chat cascade,
directory identity binding, bounded keyword retrieval and parent-generated citations are
verified. Forgetting invalidates older model context/checklists without silently deleting
visible transcripts. Retrieved instructions cannot widen profiles or bypass approvals.
The fixed 32-question lexical corpus plus 64 same-project distractors passes search and
bounded-context recall@5 at 1.0 with zero foreign IDs; this is not semantic quality evidence.

Final default 453 passed / 50 skipped, 28 frozen checks and both final rendered memory
flows pass; source/frozen parity covers 16 modules. Earlier actual Qwen restart recall
passed, but current owned Ollama returns zero models and logs manifest access denied.
Current real-model revalidation is blocked, not missing memory functionality; P1-03 A
remains unchecked. Recovery/evidence: docs/project-memory.md and IMPLEMENTATION.md.
Embeddings, file/chunk ingestion, stale-source/version reindexing and vector deletion
remain unimplemented P1-03 B. No automatic crawl, cloud fallback or new vector service.

## P1-06 message/export gate recovery (2026-10-25)

The prior missing actual-model validation is now complete: both chat/slash UI scenarios
pass without skips (62.526s) against existing qwen3.5:9b/Ollama0.40.7 with isolated data.
20 history,3 discovery,3 affected source UI and3 packaged UI checks pass; Ruff passes.
Native connection IPC is bridged; inference and backend/storage/sockets/workers are real.
No product code/assets/executable changed. One browser test fixture was isolated from
shared Vite onto its own approved ephemeral origin, with stronger URL/title/text checks.
The initial timeout and historical model failures remain recorded. B2b/B2 and parentB
close; this does not establish native installed-product acceptance or OS isolation.
Evidence: .runtime/p1-06-messages-recovered/validation.json; guide: docs/history-paging.md.

## F09 evaluation prerequisite: candidate not retained (2026-10-25)

A development-only restricted-review evaluator now provides strict source anchors,
version/grant/native/provenance checks, owned bounded workers, trusted fixture oracles
and retained role/parent records. It does not implement Studio child tasks or inherited
parent permissions. Those remain missing functionality, not merely untested features.

Actual grounded comparison covers eight inputs three times: first pass18/24, same-agent
self-review21/24 and specialist19/24 exact-location matches; zero specialist wins and two
regressions. The earlier ungrounded6/9/6 run is retained. No oracle relaxation or discarded
failure. Keep this candidate inactive; integrated delegation still requires a demonstrated
benefit and its original runtime/security gates. A0 evaluator alone closes.
Final targeted69 passed/one opt-in skipped; pre-final-guard default648 passed/61 skipped;
Ruff/wheel checks pass. See docs/specialist-review-trial.md and
.runtime/p2-04-review-trial/validation.json. Location matching is not general review certification.

## F10 optimization feasibility: request-context alignment (2026-10-25)

P3-02 A0 now measures the existing schema probe at2K versus the requested8K context
through isolated experimental client instances. All12 warm samples pass the same
microtask and applied-context/VRAM/payload checks; measured fresh-worker p50 excluding
warm setup is8.218s versus1.047s. Native loading explains most of this observed gap.
Default654 passed/61 skipped; targeted49 passed/one skipped; Ruff/wheel checks pass.
No production setting, model route, service state control or permission is changed.
Broader matched task/safety qualification and controlled model-unloaded measurements
remain missing before adoption; the warm result does not satisfy those gates. See
docs/probe-context-trial.md and .runtime/p3-02-probe-context/validation.json.

## F10 matched qualification infrastructure (2026-10-25)

P3-02 A1a adds the matched broader evaluator, rather than adopting the warm microtask's
setting directly. Both profiles reuse all20 model tasks three times and eight safety
cases, preserving grants/oracles and recording bounded native/context/request/source
receipts. Full136-workflow protocol acceptance passes. Fixed profile routing and
cancellation remain supervised; simulated observations cannot establish model quality.

The broad live corpus, controlled owned model-unloaded measurements and runtime/package
adoption checks are still missing evidence. Model access remains an external gate;
production defaults and tool/security policy are unchanged. A1/overall P3-02 are not
complete. A1a alone closes with665 default passed/62 skipped,90 targeted passed/3 skipped,
17 timing checks, Ruff and wheel/source/import evidence. Guide:
docs/probe-qualification.md; evidence: .runtime/p3-02-qualification/validation.json.

## F10 actual matched measurement: adoption rejected (2026-10-26)

The live broader measurement is now present:120 model attempts and16 deterministic
safety attempts, both profiles56/60 and8/8 respectively. Context/native/source receipts
revalidate. Worker p50 improves13.578s to7.078s with nearly unchanged generation rate,
but a case-level loss fails the predeclared nonregression gate. Aggregate equality is
not sufficient for adoption. The default remains unchanged; no case/oracle was repaired
or rerun to replace a failure. Small samples do not prove the setting caused the loss.

Thus broader measurement is verified, while qualified nonregression and controlled
owned cold/runtime adoption remain unaccepted. Existing diagnostic limitations are
explicit: shared exact-copy newline failures, a strict explicit-read oracle and an
unretained download error category. These do not establish a publisher bug or a general
browser failure. Full evidence: .runtime/p3-02-live-20261026/validation.json.


## F05 update: embedding prerequisite measured (2026-10-26)

The local embedding dependency is now installed and the first fixed actual-model study
passes its declared retrieval gate: hybrid32/32 literal,30/32 paraphrase versus lexical
32/32 and14/32 respectively, with zero cross-project results. Bounded embedding transport,
identity checks and a versioned evaluation corpus are implemented. This is distinct from
semantic feature integration: persisted vectors, source/chunk versions, stale-file/model
invalidation, derived-vector deletion and actual integrated restart/citation tests remain
open. Existing explicit memory A is retained. See ROADMAP.md P1-03 B0?B3 and
`.runtime/semantic-evaluations/3981d732a414477b99ebbd0a752cc048/report.json`.


## F05 update: explicit note-vector persistence (2026-10-26)

B1a now implements explicit confirmed indexing and authenticated hybrid note search,
SQLite v9 vector/model/source hash tracking, transactional replacement, scope/epoch/model
revalidation and forget/source-chat vector cascades. Actual source and frozen-sidecar
workflows have exercised restart, authenticated lookup, source preservation and forget.
Full regression evidence belongs to IMPLEMENTATION.md. Automatic prompt/index UI
integration remains B1b; selected file ingestion/chunks and modified-file invalidation
remain B2, with final integrated acceptance B3. Saved notes are still quoted historical
data and confer no authority. No general semantic-memory completion is claimed.


## F05 update: optional hybrid chat context verified (2026-10-26)

B1b now exposes index/model/confirmation/status controls and explicit per-project related-
wording context. Settings persist and bind to an index generation. Actual source and
frozen chat models recall a saved identifier after restart/new conversation with a source
citation; forgetting removes vectors/history context and blocks stale follow-ups before
task creation. Rendered source/frozen controls cover stop and delayed old-scope responses;
malicious recall still needs fresh write approval and cannot widen tool profiles. Full
808-case regression passes739/69 skipped. File ingestion/chunk provenance and modified-file
invalidation remain B2, final combined file/recall acceptance B3; full F05/P1-03 B stay open.
