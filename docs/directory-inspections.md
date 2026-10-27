# Directory-triggered read-only inspections

Open **Workspace → Directory-triggered inspections**. Choose a project-relative directory,
one to eight UTF-8 files (64,000 bytes each), a question and a debounce of 1–60 seconds.
The selected model and inference settings are saved. Enabling explicitly authorizes this
read-only workflow while Studio is open.

The directory decides **when** to inspect. The model reads the current selected files,
not a directory diff or every watched file. Runs have no prior chat, memories,
attachments, editing, command, browser or desktop tools.

## Baselines, debounce and restart

The first complete observation establishes a baseline without running a task. A changed
fingerprint must appear in matching complete observations separated by the debounce
before one inspection is queued. An incomplete observation clears the candidate, keeps
the baseline and authorizes no work.

Observations run serially, at least five seconds after the previous observation. Busy
agent work and other watches can increase that delay. One pending run per watch coalesces
further changes. Generation, baseline and the unique queue receipt commit together;
restart or duplicate delivery cannot admit the same retained trigger twice. An admitted
task never automatically replays after a crash.

Baselines and candidates survive restart. Elapsed UTC downtime counts toward debounce;
matching observations do not prove continuous stability between them. This is polling,
not an OS event journal or atomic filesystem snapshot. Changes wholly between polls
can be missed, and clock adjustments can affect timing.

## Controls and permissions

**Disable** cancels pending work and invalidates an in-flight observation/preflight.
An already admitted task keeps its separate Cancel control. Re-enabling establishes a
fresh baseline, without replaying changes made while disabled. **Open directory inspection
task** opens its conversation and evidence; a generation or model report is not
independent proof that the analysis is correct.

Automatic-work pause/resume is shared with interval inspections. Emergency stop persists
that pause across restarts; explicit confirmation is required to resume. Closing Studio
stops its owned timer/children. There is no Windows service or external webhook.

The [directory observer](directory-observations.md) excludes credentials, links, internal
state and known generated/cache directories. This read-only workflow writes no watched
project output. Its queue, audit and database changes are internal state. A replaced
project/directory or restored database identity cannot silently inherit old authority.

## Limits and troubleshooting

At most ten watches and 1,000 retained queue receipts are supported. Each observation
allows 2,000 enumerated entries **including the validation pass**, 128 files, 4 MiB read,
64,000 bytes per file, depth eight and a manifest below 64 KiB. Cooperative two-second
checks run between filesystem operations; a separate owned child has a four-second
parent observation deadline. Model metadata preflight has an eight-second deadline.
Startup/cleanup add overhead. Replies are limited to 64 KiB and reject duplicate fields
and nonfinite values. Ownership and cleanup do not provide an OS sandbox.

An **incomplete** result causes no inspection: choose a smaller readable directory and
check excluded/deep/oversized inputs. For changed input, unavailable models or a full
queue, review the fixed status and retained history before re-enabling. Do not broaden
permissions to hide a failure. No unrelated Python/Ollama process is terminated.

Enabled watches protect their conversation from bulk retention. Confirmed conversation
deletion cascades watches and receipts. Backups contain private, unencrypted objectives
and paths. After restore, review and recreate watches for the new database identity.

## Verification

Run `python -m unittest tests.test_directory_snapshot tests.test_probes tests.test_watches tests.test_watches_http.WatchHTTPTests -v`.
After building the frontend, set `LIVE_STUDIO_UI=1` and run
`python -m unittest tests.test_watches_http.WatchUITests -v`. Rendered tests require Edge
and an unused localhost port 1420. Tests use real files, SQLite, HTTP, owned processes,
restart/restore and workers, with explicit inference/native-IPC protocol fixtures.
Actual-model quality and installed native-product acceptance remain separate gates.
