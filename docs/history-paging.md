# Studio history paging

The read-only history API uses the existing localhost session authentication and origin
checks. It grants no tool permissions. Legacy endpoints remain compatible. The desktop
conversation sidebar, transcript and Task history use paged reads. Message/export
protocol integration and the actual-model chat/slash UI regressions pass. Browser tests
bridge native connection IPC; installed native-product acceptance remains separate.

| Endpoint | Scope |
| --- | --- |
| `GET /history/conversations` | Conversation metadata; optional `query` title substring |
| `GET /history/conversations/{id}` | Single conversation's id/title/created metadata |
| `GET /history/conversations/{id}/messages` | One conversation's visible transcript |
| `GET /history/conversations/{id}/export` | Complete stored Markdown transcript, subject to explicit caps |
| `GET /history/tasks` | Task metadata; optional `conversation` filter |
| `GET /history/tasks/{id}` | One task's metadata, including retained ownership state |
| `GET /activity` | Latest50 task metadata plus every owned worker slot and current approvals |

Paged endpoints return `{items, next, limit, order}`. `limit` defaults to 50 and must be 1–100.
Pass a returned `next` as the next request's `cursor`; null means there is no older page.
Conversations/tasks are newest first. Each message page is oldest first, suitable for
prepending; the first message page contains the newest messages. Equal timestamps keep
insertion order. Task result blobs and attachment bytes are excluded; message metrics
and attachment metadata remain available. These are row bounds, not a byte-size promise
or a full transcript export.

Cursors bind the database identity, resource, conversation and exact search string.
Changing scope/search requires starting a new first page. Restarting the same database
does not invalidate a cursor; moving it to a different store fails safely. Malformed,
oversized or mismatched cursors return 400. Invalid page sizes return 422 at the API.
Missing conversations return 404, while empty existing conversations return an empty page.
Title search treats `%`, `_` and quotes literally and uses Unicode case folding; the
query is limited to 120 characters.

Pages use indexed `(created,rowid)` positions rather than offsets. Deleting a pivot row
does not invalidate subsequent navigation. They are live views, not point-in-time backups:
concurrent deletions can shorten pages and backdated inserts/rowid reuse can affect later
pages. Refresh the first page to observe new head entries. The search filter may scan
titles; this is not a full-text index or relevance engine.

Schema v4 adds five indexes transactionally. It preserves chats, messages, attachments,
preferences, project memory, identity and execution records. It performs no tool replay
or file migration. Visible transcript pages include retained pre-forgetting messages;
the separate model-context epoch filter remains unchanged. See SQLite's official
[scrolling-window queries](https://www.sqlite.org/rowvalue.html#scrolling_window_queries).

Run `python -m unittest tests.test_history tests.test_migrations tests.test_studio_socket -v`
from the repository root. The socket suite exercises actual authenticated HTTP; set
`FROZEN_BACKEND_TEST_EXE` to a rebuilt sidecar to exercise packaged behavior. No model,
desktop input or external website is required. Desktop paging and explicit export limits
must be tested separately before marking B2 complete.

The conversation sidebar requests50 rows, shows how many are loaded, and offers **Older
conversations** when another page exists. Search runs against stored titles, including
older chats not yet loaded; changing search restarts paging and ignores late old replies.
The selected older chat stays pinned when search is empty, preserving its title and
transcript across refresh/rename. Explicitly loading older pages grows the visible list;
the count is not the total number of saved chats.

## Task navigation and current activity

Task history shows one50-run window with **Older**, **Newer** and **Latest** controls.
Older windows remain selected during task updates and reconnect. Open a run to inspect
its existing diagnostics/journal; its metadata stays pinned when it falls outside the
latest50 global entries. Selecting history never replays tools or grants permissions.
Late responses from a deleted chat cannot reopen its activity or show a stale404 alert.

Current activity is separate from historical paging: `/activity` and WebSocket snapshots
include the latest50 metadata rows plus every worker still owned by the supervisor, even
when backdated or waiting for cleanup/storage. Those states retain emergency stop.
Default activity prefers a scoped owned run; an explicitly selected historical run wins.
Approvals remain global and identify their originating conversation. These responses
exclude result blobs, memory references and private runtime errors; legacy `/tasks` stays
compatible for existing integrations. The global row bound is50 plus owned worker slots.

Validation traverses251 actual stored runs across six pages with reconnect, approval
denial, stop and delayed deletion responses. All38 packaged integration checks and final3
affected UI scenarios pass;19 Node checks include retained-owner selection/scoping.
Model/native IPC in those UI scenarios are fixtures; this does not certify real-model
quality, native Windows packaging, general checkpoint resume or database backup.

## Message navigation and export

The chat shows one50-message window. **Older messages** moves to an older window;
**Newer messages** retraces pages, and **Latest messages** returns to a fresh latest page.
The page count is a navigation position, not a total-message count. Conversation changes
clear the prior window, and late responses cannot replace another selected conversation.
Live completion and WebSocket reconnect preserve an older window; return to Latest to
see new replies. Sending a new instruction explicitly returns to the latest page.
Paging changes display only: model context still uses its existing epoch/budget/compaction
rules. Memory message selection uses the currently loaded message window.

**Export** and `/export` retrieve the complete committed visible transcript independently
of the displayed page. Title, messages and attachment metadata share one SQLite read
snapshot. The result includes all committed messages at capture time, including visible
pre-forgetting history; pending generation buffers are excluded. Attachment bodies,
metrics and project files are excluded. This is a transcript export, not a database backup.

Limits are5,000 messages and8MiB of UTF-8 Markdown. Exceeding either returns a clear error
and produces no partial download. The UI verifies completeness and byte count, then reports
the exported count/size. Export's stable tooltip remains “Export conversation as Markdown”;
its accessible description states the limits. Read-only metadata checks and selecting one
attachment avoid materializing the full transcript or unrelated attachment blobs.

Current validation: unit/API/protocol and packaged paging/export checks pass. Both actual
model chat/slash UI cases now pass without skips (62.526s), reusing the existing Qwen
service and frontend with isolated test backends/data.20 history,3 discovery and3 source/
3 packaged affected UI checks pass. No production source/assets/binary changed.
The adjacent browser-preview test now uses an owned ephemeral fixture origin and checks
its returned URL/title/text; the shared Vite route had served Studio HTML instead.
The initial timeout is retained; no claim that every browser-start delay is explained.

The earlier two real-model UI failures and owned-start manifest-denial attempt remain
historical evidence, not retroactive passes. For a future retry, run
`.\.venv\Scripts\python.exe .runtime\p1-06-messages\run_actual_ui.py`: it checks readiness,
reuses an existing service or the existing owned lifecycle, and runs actual UI only when
the configured model is listed. It closes only its owned service and records the outcome.
Preserve historical logs before rerunning that helper. Current closure evidence is kept
separately in `.runtime/p1-06-messages-recovered/validation.json`.
