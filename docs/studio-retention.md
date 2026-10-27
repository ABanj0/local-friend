# Manual conversation retention

Open **Models & settings → Conversation retention**. Set an age in days, a number of
recent conversations to retain, and a batch size. **Save retention settings** persists
the policy without deleting anything. Defaults are 90 days, 50 recent conversations
and 20 per batch. No scheduled cleanup runs.

Choose **Preview retention**, inspect the titles and related-record counts, then select
**Review retention deletion**. Cancel or Escape closes the confirmation without deletion.
Only **Delete reviewed conversations** applies that exact batch. Every further batch
requires a fresh preview and explicit confirmation. The policy spans this Studio's stored
conversations, including chats from different projects.

Age and recent protection use the latest stored activity across conversation creation,
messages, tasks, events, goals and saved memories. The selection at preview time,
unfinished goals, pending uploads and nonterminal tasks are excluded. Retention settings,
preview and deletion refuse while any owned worker or cleanup remains, during shutdown,
pending restore restart, or emergency stop. This avoids racing active agent work.

A preview lasts five minutes and exists only in the current backend process. Editing
settings, changing selection, restarting or changing reviewed data requires a new preview.
The server compares exact affected data again inside the deletion transaction; changing
a title, message, attachment bytes or affected memory context invalidates the review.
Deletion is atomic across the batch, including dependent attachments, tasks, goals,
execution journals, events and independent verification records.

Source memories disappear with their conversations. Other conversations in the affected
memory scope retain their visible transcripts but reset future model context, preventing
forgotten notes from surviving through old model history. The preview reports this count.
The last aggregate batch receipt survives restart; it contains no message or memory bodies.

Project files, downloads, private backups and all restored generation folders remain
untouched. Deletion is not secure erasure: SQLite free pages and retained backups may
contain old data. Chat export supports up to 5,000 messages / 8 MiB and excludes attachment
contents. Use a private Studio backup to preserve complete database state before pruning.

Policies accept ages 1–3,650 days, 0–5,000 recent conversations and batches of 1–50.
Each review is bounded to 50,000 related rows / 64 MiB and a cooperative five-second
processing budget. Oversized batches fail safely: lower the batch size. A single oversized
conversation may need individual review. Expired, stale or interrupted requests must be
resolved by refreshing history and previewing again; do not blindly repeat deletion.

Authenticated integrations use `GET /retention`, `POST /retention/policy`,
`POST /retention/preview` with `{"protected":["<selected-conversation-id>"]}`, and
`POST /retention/apply` with `{"preview":"<review-id>","confirmed":true}`. No paths or
caller-supplied deletion lists are accepted. The API is unavailable to model tools.

Run `python -m unittest tests.test_retention tests.test_retention_http -v` for source and
real runtime checks. The opt-in rendered retention scenario exercises actual HTTP/SQLite,
keyboard confirmation, stale responses and an owned approval wait. Its inference/native
bridge are explicit fixtures; it does not certify actual-model quality or native packaging.
