# Studio database backups

Open **Models & settings → Studio data backup → Create Studio backup**. Review the
private-data notice, then choose **Save backup**. Escape/Cancel saves nothing. The result
shows the generated filename, exact byte count, schema version and SHA-256. Backups go
only to `backups/` inside the configured app state directory (development default:
`.runtime/state/backups/`). No destination path is accepted from chat, tools or the API.

Backups contain complete stored chats, binary attachments, goals, preferences, explicit
project memory and derived note vectors, task/verifier/event records and the execution journal. They are unencrypted
private database files, rather than redacted diagnostic exports. They exclude repository
files, model weights, `agent.toml`, transient approvals, in-memory generation and screen
previews. Losing that surrounding data cannot be repaired by a database backup.

The backend requires no owned task, including approval waits, cleanup and storage retry.
It also refuses shutdown or a latched emergency stop. The control is disabled during known
activity; backend enforcement applies even if a caller bypasses the UI. Creating a backup
does not change tool permissions or request inference.

The implementation uses [SQLite's online backup API](https://www.sqlite.org/backup.html)
through [Python sqlite3](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup),
so committed WAL data is included and uncommitted writes are excluded. The staged snapshot
must pass current schema/migration, store-identity, integrity and foreign-key checks without
migration or repair. The published copy uses rollback-journal mode and needs no WAL/SHM
companions. Publication is exclusive and never replaces an existing filename.

Limits:512MiB per accepted snapshot,20 directory entries and a30-second processing deadline
checked during copying, SQL validation and hashing. Disk/OS calls can still depend on the
host. Unknown partial entries are preserved; failed attempts clean up only their own staging
entry. A crash may leave a partial entry, which is not a successful backup. There is no
automatic pruning. Keep saved copies private and manage them explicitly while Studio is
closed. Do not copy only the live SQLite main file while WAL is active.

Authenticated integrations can `POST /backups` with exactly `{"confirmed":true}`. Other
body fields are rejected, including destination paths. This endpoint returns metadata,
not database bytes. The SHA-256 supports comparison; it is not a signed authenticity proof.

To restore, select **Saved backup**, choose **Inspect backup**, then **Restore selected
backup**. Review the filename/hash and data-change notice; **Restore and restart** confirms
the action. Escape/Cancel leaves current data selected. Restoring needs two free backup
slots and one of five staging slots. Task approval waits, cleanup/storage ownership,
shutdown and a latched emergency stop refuse the action.

Studio validates a fresh prepared database, saves current data to a fresh rollback copy,
then selects that generation for the next backend start. The existing native restart
command stops only Studio's owned backend. Old authenticated requests drain before the
selection changes; new data routes refuse work until restart. Original databases remain
intact. **Restore previous state** runs the same confirmed workflow using the latest
rollback copy, preserving the state being left as well.

Stored history, attachments, goals, preferences, memory and execution records return;
unsent drafts, transient approvals and pending generation do not. A new database identity
resets event/history cursors; stale replies from the old backend cannot overwrite the new
settings or selection. A saved task is historical evidence, not a resumable checkpoint or
current verification of project files. Retention remains separate B4 work.

Run `python -m unittest tests.test_backups tests.test_migrations tests.test_history -v`.
The rendered backup test in `tests.test_tool_profile_ui` exercises real authenticated HTTP,
SQLite, worker ownership and denial; its inference/native bridge are explicit fixtures.

## Restore preparation API (B3b1)

Authenticated callers can rehearse recovery with `POST /restore/prepare` and exactly
`{"backup":"<32-lowercase-hex-id>","sha256":"<64-lowercase-hex-hash>","confirmed":true}`.
Use the ID/hash returned when creating a backup. No uploaded file, URL or destination path
is accepted. Preparation refuses owned tasks, shutdown and emergency stop.

The selected standalone backup is checked for links, size, exact hash, current version,
migration history, integrity, references and reviewed schema. Unexpected triggers, views
or custom indexes are rejected; nothing is dropped or migrated to make input acceptable.
Whitespace and SQLite's legacy identifier quoting may vary; SQL literal values stay exact.
A source that changes during preparation fails before readiness. Journal companions are
refused, so select the standalone file created by Studio's backup action.
Copying checks the opened file's identity before reading, compares its hash/identity again
afterward, and parses only the private staged copy. SQLite does not reopen the source path.

Prepared data goes into a new generated directory under `restore-staging/` in app state.
All records retain their IDs/data; only the database store identity changes, so a future
activation can invalidate old history/event cursors. A separate online rollback snapshot
captures current stored data. `ready.json` is written last, after validated database and
rollback publication. The response contains metadata/hashes and `activated:false`.

Without the explicit activation step, the current database remains active, including
across an ordinary backend restart.
Preparation cannot replay actions, restore transient approvals or start a model. Interrupted
copies without a ready marker are unaccepted drafts. Cleanup removes only entries created
by that call; unknown files and replacement directories survive. Completed rollback copies
also survive a later preparation failure. There is no automatic cleanup of crash leftovers.

Limits are5 staging entries,512MiB per database and a cooperative60-second processing
deadline. These private, unencrypted copies consume disk space independently of backups.
Activation consumes the exact prepared database hash and validates it again. It takes
another current rollback snapshot after draining requests, so changes made after
preparation are retained. A failed preparation never activates itself.

Run `python -m unittest tests.test_restores tests.test_restore_http -v`. Tests compare every
nonempty required table, retain binary attachments/memory/journal/verifiers, verify actual
process crashes before rollback/ready, and exercise the real runtime over HTTP and restart.

## State ownership and recovery

Only one supported backend can own a configured state directory. A process-lifetime file
lease is acquired before Manager recovery, including when different ports are requested.
An abrupt process exit releases the OS lease; the small lock file remains for reuse.
Close older Studio versions before upgrading, since they do not implement this lease.
This is backend ownership, not OS isolation of repository code.

`studio-current.json` selects an app-generated directory under `restore-staging/`.
The selected directory contains active data after restoration: keep it intact. The original
`studio.sqlite3`, backups and unselected generations remain available. Unknown, malformed,
linked, missing or identity-mismatched selections fail startup clearly; Studio does not
silently replace them with an empty database. Backups and benchmark/evaluation idle checks
follow the selected database.

Before selection publication, a failure leaves the current choice unchanged. Once
publication is attempted, failure can mean an unknown outcome: old APIs require restart
and no blind undo or repeated action occurs. Restart and inspect the active history.
Original data and completed rollback copies remain retained in either case.

For a damaged selection, close Studio and preserve a copy of its state directory first.
Restore a known-good selection file, or move only `studio-current.json` aside to reopen the
retained original `studio.sqlite3`. Keep every generation and backup until recovery is
verified. This is an explicit offline recovery action; do not replace a live SQLite file.

Authenticated integrations use `GET /backups` for a bounded metadata inventory,
`GET /backups/{id}` for exact hash inspection, and `GET /restore/status` for the active
generation/rollback IDs. Inspection does not certify schema. `POST /restore/activate`
accepts exactly `{"preparation":"<id>","sha256":"<prepared-database-hash>","confirmed":true}`.
After publication, only authenticated health remains available until backend restart.
Health includes `restore_pending`; WebSockets close with restart code1012.

Run `python -m unittest tests.test_state_owner tests.test_state_owner_http tests.test_restore_activation tests.test_restore_activation_http -v`.
The rendered restore scenario uses actual APIs, SQLite and two backend restarts, while
native IPC and inference are explicit fixtures. Installed Windows/WebView acceptance
remains separate. The agent-after-restore regression uses a real owned worker, approval,
file publication and artifact evidence, with a protocol inference fixture.


The current database schema is v10, including private derived memory indexes/vectors and
explicit file-source/chunk provenance. Backup/restore tests preserve populated source/chunk
and vector tables and exact binary payloads. Original project files are not backed up by
this database snapshot. File freshness is rechecked before memory context admission. Existing
strict schema compatibility remains: an older-schema backup needs a matching application
version to restore it, followed by the ordinary live-database upgrade. Do not edit or
migrate the original backup in place. Vector identity is rechecked against Ollama on
explicit semantic search; backup presence does not certify the currently installed model.
