# Explicit project memory

Open **Project memory** in Studio. Choose an existing directory inside the configured
workspace, then save a note or select a message from the current chat. No files are
crawled, messages automatically remembered, or notes created by the model. Selected
messages are snapshots, not endorsements of their claims. Use `/remember <note>` and
`/recall <keywords>` from the composer; these commands do not need inference.

Search returns up to five keyword matches by default. After indexing, choose **Related wording
(local model)** in **Search mode** for semantic search. An empty search shows the newest 100 notes.
Each note has a `memory:<id>` reference, source chat, optional source message, timestamp,
and SHA-256 of its exact text. **Open source chat** shows the original conversation.
Use **Forget**, or `/forget <id>`, to open a confirmation. There is no automatic expiration.

For subsequent model tasks, Studio searches using the current user instruction, with keyword
retrieval by default or related-wording retrieval when explicitly enabled for this project. It
adds bounded, explicitly untrusted excerpts to that user message. At most five records
and 8,192 serialized record characters are included; long notes use 900-character excerpts
near a matching word. The recorded hash still identifies the complete saved note.
The parent backend appends source IDs to the final response. The footer identifies
retrieved context, not proof that the answer used every note or independently verified it.
Agent approvals, tool profiles, filesystem scopes and verification requirements remain
unchanged. `/test` and `/diff` do not retrieve memory.

Explicit notes began in schema v3; the current database is schema v9. Keyword memory
requires no additional service, model, API key or dependency. Directory identity includes canonical path and filesystem
identity: moving or replacing a project does not silently transfer its memory. Every
read/delete recomputes the approved project scope; knowing a note ID is insufficient.
Once a conversation stores or retrieves memory, using another project requires a new
conversation. Root workspace memory is separate from each subdirectory's memory.

Forgetting, deleting a selected source message, or deleting its source chat removes
the note through SQLite foreign-key cascades. It also advances the project's context
epoch: older messages and generated goal checklists in memory-bound conversations
are excluded from future model requests. Their visible transcripts/checklists remain
for review. Regeneration cannot resurrect an excluded turn. Memory changes and source
deletion are blocked while an affected task holds a snapshot; stop/finish it first.
This is logical deletion, not secure erasure of SQLite pages, WAL files, exports or backups.
Delete relevant chats separately to remove their visible transcripts.

Limits: 1,000 notes per project; each note 4,000 characters and 8 KiB maximum; queries
500 characters. Known credential patterns, launch credentials and control characters
are rejected. Credential detection is not exhaustive: do not save secrets. Keyword
search normalizes Unicode/case but does not perform stemming, translation or semantic
matching. Optional embeddings, vector deletion and related-wording controls are described
below. File ingestion and stale-chunk detection remain P1-03 B2. This feature does not
provide OS isolation or a durable execution checkpoint.

Verify with `python -m unittest tests.test_memory tests.test_migrations -v`.
Set `LIVE_MEMORY=1` for actual local Ollama restart/recall acceptance; it is skipped by
default. Set `LIVE_STUDIO_UI=1` for the rendered memory scenario in
`tests.test_tool_profile_ui`. Protocol fixtures and actual-model evidence are reported
separately. Migration preservation, rollback and cascade behavior use real SQLite;
[SQLite documents per-connection FK enforcement and cascade actions](https://www.sqlite.org/foreignkeys.html).

## Model-access recovery and earlier owned-startup failure

The existing normal-session local service is independently usable from managed validation.
Actual Qwen restart/recall/citation/forget acceptance passed2026-10-24 (1 test,zero skipped,
3.417s). P1-03 A is complete alongside current storage/process/frozen UI gates. No service,
model or ACL change was made to obtain this result.

Earlier owned-server attempts logged `bad manifest ... Access is denied`, exposing no
models even though Python could read manifests/blobs. Those logs remain; the specific
denied operation is unproven. Existing-service reuse verifies the memory path, not a
repair of owned startup. DNS and account1909 are separate issues.

1. In your normal, non-administrator PowerShell, run `cd C:\path\to\local-friend`.
2. If Ollama is already running, reuse it. Otherwise run `./scripts/start-model.ps1` and
   leave that terminal running for the diagnostic. Do not run a second server on its port.
3. In another normal PowerShell, run `./.runtime/ollama/ollama.exe list`. The configured
   `qwen3.5:9b` must appear; HTTP readiness alone is insufficient.
4. Run `$env:LIVE_MEMORY='1'`, then
   `./.venv/Scripts/python.exe -m unittest tests.test_memory.LiveMemoryTests -v`.
   Clean up the flag with `Remove-Item Env:LIVE_MEMORY -ErrorAction SilentlyContinue`.
5. If the manifest still reports access denied, retain the server error and model-list
   output for diagnosis. Do not delete/re-pull the existing model, change ACLs, or elevate
   the server to mask an unidentified permission failure. If the normal-session service
   works, keep it running and resume managed validation against that existing service.

Reusing the existing normal-session service has now passed managed memory acceptance.
The owned diagnostic servers were shut down; no unrelated Ollama process was terminated.

## Semantic retrieval dependency (P1-03 B)

Explicit keyword memory A is complete. B now has a first evaluated local embedding model; it still needs
approved source/chunk hashes, stale-source/model reindexing, scoped cosine retrieval and
deletion propagation. The owner installed qwen3-embedding:0.6b on2026-10-26. The official
[Qwen3 embedding catalog](https://ollama.com/library/qwen3-embedding) lists the0.6b model
at639MB; [Qwen's retrieval instructions](https://github.com/QwenLM/Qwen3-Embedding) and
[Ollama's embedding API](https://docs.ollama.com/api/embed) guide evaluation, not a quality
claim. Existing32-question keyword recall is already perfect; semantic integration must
demonstrate useful paraphrase retrieval without regressing safety or literal recall.

Managed acquisition failed to connect to registry HTTPS with Windows socket permission
denial10013. It used a separate owned server/cache; it did not alter the chat model,
existing service or network controls. The current checkout already has a working local
Ollama service. To acquire this dependency through that approved service's model store,
run the existing installer from a normal, network-authorized PowerShell at the repository root:

```powershell
.\scripts\pull-model.ps1 -Model 'qwen3-embedding:0.6b'
if ($LASTEXITCODE -ne 0) { throw 'Embedding download failed; preserve its output.' }
(Invoke-RestMethod http://127.0.0.1:11434/api/tags).models | Select-Object name, digest
```

The script targets the current localhost11434 service and leaves agent.toml's chat-model
selection unchanged. Leave that service running for evaluation, without submitting
competing tasks. Do not use the managed runner's existing service as a network proxy;
the acquisition above is an ordinary authorized owner-session action. The model tag and
pull command are documented in the [official model card](https://ollama.com/library/qwen3-embedding:0.6b).

The old `.runtime/p1-03-semantic/acquire_model.py` was a private acquisition diagnostic,
not a shipped setup command. Do not rerun it in place: it overwrites acquisition.json.
Its original failure evidence is retained. Separate-cache diagnostics must use a new
owned case and preserve existing caches/processes. If normal authorized acquisition also
fails, retain the error; no firewall/ACL workaround or cloud fallback is part of this setup.

The first actual comparison is recorded in
`.runtime/semantic-evaluations/3981d732a414477b99ebbd0a752cc048/report.json`.
The immutable corpus uses32 existing literal questions plus32 paraphrases,64 distractors,
and32 identical notes in another project. Equal reciprocal-rank fusion retains32/32 literal
matches and finds30/32 paraphrases (93.75%), versus14/32 lexical (43.75%); no cross-project
results. The predeclared gate required no literal loss, at least90% paraphrase recall and
at least10 percentage points of gain. Zephyr and Acorn paraphrases remain misses; this
single synthetic corpus is not evidence of universal retrieval quality.

The study is development evidence. Explicit note-vector indexing/search is now implemented
through authenticated integrations (below); file-source chunks and their final acceptance remain B2/B3. An embedding model is not a second chat/tool routing
candidate. No chat model/default was changed.

Run the isolated study only while Studio is idle:

```powershell
.\.venv\Scripts\python.exe -m local_agent.semantic_evaluation
```

Each run creates an exclusive `.runtime/semantic-evaluations/<id>/` with an isolated SQLite
store, bounded vectors in memory, content-free observations and model/native timing receipts.
There is no cloud fallback, model download or production index activation. Protocol fixtures
cannot establish a quality pass. The client disables truncation/redirects/proxies, validates
local model identity/dimensions before and after each bounded batch, and closes only its
own request socket on its absolute deadline. Query instruction format is versioned.
Do not change corpus v1 or retry failed cases to manufacture a passing result.


## Explicit note-vector API (P1-03 B1a)

This optional API indexes only notes already saved through **Remember**. Confirmed indexing
keeps keyword context selected. B1b now adds the controls and an explicit related-wording
context switch described below. `/recall` remains the deterministic keyword shortcut; source
lookup and tool permissions retain their existing behavior.

An authenticated integration using the current desktop-session bearer credential can:

- `GET /memory/index?project=.`: inspect local index counts and state. `locally_current`
  means saved-note hashes/epoch/counts match; `model_check: not_checked` explicitly means
  this status request has not contacted Ollama.
- `POST /memory/index` with exactly
  `{"project":".","model":"qwen3-embedding:0.6b","confirmed":true}`: confirm embedding
  the already saved notes. Choose an installed local embedding-capable model; model
  names are not command lines or endpoints. Missing/false confirmation changes nothing.
- `GET /memory/hybrid?project=.&query=<URL-encoded question>`: return up to five scoped
  notes with their existing IDs, source-chat/message references and exact text hashes.
  The same declared cosine/RRF algorithm is shared with the fixed evaluation.

Keep credentials in the existing authenticated connection, not URLs, saved notes or logs.
All routes retain localhost/origin/session authentication and approved project scopes.
Reindex/search refuse active tasks and reserve one embedding operation. New tasks refuse
admission until that operation ends; Stop/shutdown remains available. Network calls occur
outside Manager's lock. Host cancellation interrupts the owned HTTP reader without killing
Ollama or Python processes. Requests and the full reindex/query have bounded deadlines.

Schema v9 stores normalized little-endian float32 vectors, vector checksums, note hashes,
model/digest/server/dimension/query-format identity, scope, note-manifest/forget epoch and
an exclusive index generation. Publication is transactional: failed inference, concurrent
notes/project/index changes, Stop or shutdown preserve the previous index. Query rechecks
current model identity before sending the question and revalidates its snapshot before
returning results. Model/version/dimension changes require an explicit reindex. There is
no silent cloud/lexical fallback from this semantic endpoint.

Saving/forgetting notes makes the old index stale until explicitly reindexed. Forget and
source-chat deletion immediately cascade their vector rows; they still invalidate earlier
memory-influenced model context. No secure disk erasure is claimed. An index remains
private database data and is included in confirmed backups. Explicit file ingestion and
changed-file invalidation are described below; saved notes remain historical snapshots.

Run deterministic index/API/migration contracts with
`python -m unittest tests.test_memory_index tests.test_embeddings -v`.
`LIVE_EMBEDDINGS=1` separately enables the actual local embedding/index contracts; skipped
live cases do not verify a model. The B1a frozen-sidecar acceptance exercised real HTTP,
actual embeddings, restart, source preservation, authentication and forget. It verifies
backend functionality, not native desktop rendering or the pending automatic-memory UI.


## Related-note context in Studio (P1-03 B1b)

1. Open **Project memory**, select an approved project and save notes as usual.
2. Choose **Index saved notes**. Select an installed embedding-capable model and confirm
   **Index notes**. The tested candidate is `qwen3-embedding:0.6b`; the chat-model selection
   stays unchanged. Other embedding models require their own retrieval evaluation.
3. Choose **Enable related-note context**, review the project scope, then **Enable retrieval**.
   **Chat context: Related wording** confirms the setting. Future chats, plans and agents
   use bounded hybrid retrieval from this project's notes, with the existing source footer.
4. Choose **Use keyword context** to return to the original keyword behavior, including
   while the embedding service is offline. `/test`, `/diff` and selected-file inspections
   never request memory embeddings. `/recall` stays keyword-only.

Search mode is independent: choose **Related wording (local model)** for an explicit note
search even when chats use keywords. Empty searches still list the newest100 notes.
Indexing, semantic search and enabling validate current model metadata; local status alone
states only whether saved notes match the index. Settings/indexes persist across restarts.

Reindexing deliberately selects keyword context until you enable related wording again.
New/forgotten notes make the prior index stale: reindex current notes, or choose keyword
context. A stale enabled index blocks task admission with a clear error; it never silently
uses stale vectors. Forget/source-chat deletion cascades vectors and excludes earlier
memory-influenced history, while visible transcripts remain. Switching to keywords alone
does not erase prior conversation history or saved notes.

Confirmation dialogs close when their requests start, keeping the global **Emergency stop**
available. Cancel/Escape before confirmation sends no indexing request. Stop closes only
owned embedding HTTP requests and prevents publication/admission; it does not terminate
shared Ollama. Network preflight runs outside the cancellation lock. Before creating a task,
Studio revalidates its effective regeneration instruction, conversation history, source scope,
forget epoch, index generation and explicit setting. Recall carries no reusable approvals.

Actual source and frozen backends passed real embedding/chat recall after restart/new chat,
source citation, forget/vector removal and stale-admission refusal. Rendered source and
frozen-backend UI tests passed confirmations, search, stop, scope switching and ignoring
late old-scope responses. Rendered tests use a browser IPC bridge/protocol model fixture;
they do not establish native WebView2/installer acceptance.
Evidence: `.runtime/p1-03-memory-integration/validation.json`.

## Explicit file sources (P1-03 B2a/B2b)

In **Project memory → Saved file sources**, enter a project-relative UTF-8 path such as
`docs/decisions.md`, choose **Preview file**, review every excerpt and confirm **Save file
memory**. Cancel/Escape saves nothing. The existing **Choose project** control selects the
approved root. No directory is crawled. If no conversation is selected, confirmation creates
a source chat automatically. Its deletion will remove those excerpts.

The source list displays saved metadata; **Check sources** observes current files. A stale
source remains visible. **Review reimport** previews fresh bytes, and **Replace saved
excerpts** requires explicit confirmation. A file changing after preview refuses import;
review it again. **Forget saved file → Forget all excerpts** removes derived data only.
Reindex saved notes after import/replacement if using related wording. Navigation discards
late previews/metadata from prior projects. Pending requests close modals and leave the
global Emergency stop available. Original files remain unchanged by these operations.

The same authenticated API saves approved files as historical memory.
Use the existing connection bearer token, protected like other privileged API credentials:

1. `POST /memory/sources/preview` with `{"project":".","path":"docs/decisions.md"}`.
   Review the returned path, raw SHA-256, resource version, chunk text and spans.
2. `POST /memory/sources` with the same project, a source `conversation` ID, the preview's
   exact `path`, `sha256`, `version`, nullable `expected_generation`, and `"confirmed":true`.
   Reimport requires a fresh preview; changed bytes, file identity or saved generation refuse
   publication. The transaction replaces all derived excerpts together, preserving originals.
3. `GET /memory/sources?project=.` lists saved source metadata. `POST /memory/sources/check`
   with the project checks current sources. Import never runs a model. Explicitly reindex
   saved notes and enable related wording if desired; a changed manifest requires reindexing.
4. `POST /memory/sources/{id}/forget` with project and `"confirmed":true` removes that
   source's entire excerpt/vector set. Forgetting any one of its memory excerpts does the
   same, with a whole-source confirmation. Source-chat deletion also cascades derived data.

Limits:16 sources/project,64,000 raw bytes/file,80 chunks/source,900 characters/chunk and
1,000 total notes/project. Empty, binary, non-UTF-8, control-containing or recognized private
content is refused before chunking. Credentials, internal state, dependencies, links and
paths outside approved project scope are excluded. Detection is not a guarantee that every
possible secret format is recognized; review selected text before saving it.

Raw hashes describe original bytes. UTF-8 BOM removal and universal-newline normalization
produce `utf8-bom-newlines-v1`; zero-based start/end character offsets are half-open in that
view, while displayed line spans are one-based. Whitespace-only segments are omitted.
Each excerpt retains its own normalized hash, source raw hash/version and generation.

Before search, indexing or model-context admission, bounded file reads occur outside the
cancellation lock. Current metadata and cached chunk layout/text/hashes are revalidated.
Changed, missing or unsafe sources become stale, immediately lose vectors and invalidate
earlier memory-influenced model history. Stale excerpts remain inspectable in empty listings
and source lookups, but are excluded from keyword/hybrid recall. A stale enabled index blocks
admission until reindexing or explicit keyword selection; reimport never happens silently.
During active work, human inspection uses labelled saved snapshots without file reads;
those cached receipts cannot admit model context. Observations are point-in-time, not
filesystem verification, execution authority or an operating-system isolation boundary.

Schema10 source/chunk data is included in private database backups and confirmed retention
reviews. Original files remain untouched. Tests: `python -m unittest tests.test_memory_sources
-v`; `LIVE_MEMORY_SOURCES=1` adds the real local embedding/chat restart/change workflow.
Actual source/frozen workflow evidence: `.runtime/p1-03-memory-sources/validation.json`.
Rendered source/frozen control evidence: `.runtime/p1-03-memory-source-ui/validation.json`.
These browser IPC fixtures verify frontend/backend workflows, not native-window packaging.

## Integrated qualification (P1-03 B3)

The fixed v1 corpus also passes through the production file-memory/index/search paths:
16 approved files containing32 unchanged facts,64 same-project distractors and32 matching
notes in another project. After backend restart,64 queries produce literal recall@5 of
32/32 and paraphrase recall@5 of30/32 (93.75%), versus keyword14/32, with zero cross-project
results. Zephyr/Acorn remain misses. These bounded measurements do not imply universal
retrieval accuracy or current-file verification. The corpus and prior failed observations
remain unchanged. The same actual-model run verifies citation/provenance, stale admission,
history/vector invalidation, whole-source forgetting and source-chat cleanup.

Run explicitly with `LIVE_MEMORY_ACCEPTANCE=1` and
`python -m unittest tests.test_memory_acceptance -v` in the project environment. This uses
real local models in a disposable workspace and refuses to compete with an active Studio
task. It writes one report under `.runtime/memory-acceptance/` even if a later check fails.
Ordinary discovery skips this opt-in; skipped execution does not qualify a model.
Evidence: `.runtime/p1-03-memory-acceptance/validation.json`.
