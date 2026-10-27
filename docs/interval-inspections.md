# Scheduled read-only inspections

Open **Workspace → Scheduled read-only inspections**. Enter one to eight project-relative
UTF-8 file paths (64 KB each), a question, an interval in whole minutes, a missed-run
policy and a display timezone. The selected model and inference settings are saved with
the schedule. **Enable interval inspection** explicitly opts into recurring reads.
The first slot is one interval after creation; intervals range from one minute to 30 days.

## Timing and missed runs

Slots use elapsed UTC milliseconds, independent of daylight saving time. The saved IANA
timezone controls display only. For example, an hourly Toronto interval can display
01:30 EST then 03:30 EDT in spring, or two 01:30 slots with different offsets in autumn.
The UI falls back visibly to UTC if its browser cannot format a saved zone. The bundled
display-zone registry was generated from Node ICU78.3; Python tzdata is not required.

- **Run the latest missed slot once:** after downtime, enqueue only the latest elapsed slot.
- **Skip missed intervals:** discard slots when at least a whole interval has elapsed;
  ordinary timer lateness shorter than one interval still runs that slot.

Next-slot advancement and queue insertion share one SQLite transaction. A busy Studio
keeps at most one pending item per schedule; further due slots merge into that pending
work rather than creating a backlog. One task runs at a time. Clock adjustments can
delay/advance wall-clock slots and lease expiry; this is not a real-time scheduling service.

## Controls and recovery

**Disable interval inspection** cancels pending items and invalidates in-flight model
checks. An already admitted/running task retains its separate Cancel control. Re-enabling
sets a new first slot one interval from now. **Pause scheduled inspections** retains
pending work; resuming applies each schedule's missed-run policy.
This automatic-work pause also covers [directory-triggered inspections](directory-inspections.md).

**Emergency stop** cancels active tasks, interrupts owned model preflight and persists a
scheduler pause across restarts. Automatic work resumes only after **Resume scheduled
inspections**. Closing Studio stops its timer and owned children; enabled schedules are
retained and evaluated at the next launch. There is no Windows service or external webhook.

Task admission consumes a durable trigger once. A crash after admission never automatically
replays that task, even if no worker started. Review interrupted tasks before explicitly
resuming a supported inspection or starting fresh work. **Open latest inspection task**
opens the associated conversation and existing task evidence; a model report is not
independent certification of its analysis.

## Permissions, limits and troubleshooting

Runs read current selected files only: no prior chat, memories, attachments, commands,
edits, browser or desktop tools. Model metadata is checked in an owned process with an
eight-second parent deadline, then the normal supervised inspection worker rechecks it.
Missing/changed project identity or unsupported input disables the schedule; review it
before re-enabling. Model unavailability disables the affected schedule rather than
repeatedly attempting inference. Ordinary safety, state ownership and restore gates apply.

There are at most 50 retained schedules and 1,000 queue receipts (64 KiB each, 64 MiB
total payloads). When full, affected schedules stop; review retained history. Deleting a
conversation with confirmation deletes its schedules and receipts. Enabled schedules
protect their conversation from bulk retention. Backups include private, unencrypted
schedule objectives and selected paths; a restored database has a fresh identity, so its
old schedules must be reviewed/recreated rather than silently acquiring new authority.

## Validation

Run `python -m unittest tests.test_schedules tests.test_schedules_http.ScheduleHTTPTests -v`.
Build the frontend, set `LIVE_STUDIO_UI=1`, then run
`python -m unittest tests.test_schedules_http.ScheduleUITests -v`. UI tests require Edge and
an unused localhost1420 listener. They use real SQLite/HTTP/timers/workers with explicit
model and native-IPC protocol fixtures, not an actual-model quality or installed-product gate.

Implementation follows SQLite's [transactions](https://www.sqlite.org/lang_transaction.html),
FastAPI's [lifespan](https://fastapi.tiangolo.com/advanced/events/) and
[Intl date formatting](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat).
