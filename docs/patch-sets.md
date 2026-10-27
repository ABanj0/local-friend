# Reviewed related-file changes

Coding and Unified agent profiles provide `apply_patch` for related UTF-8 file creations
and replacements. Ask the agent to inspect the files, propose a patch set, run approved
tests, and report the evidence. Existing single-file editing remains available.

Each change supplies a workspace-relative `path`, full proposed `text`, and
`expected_sha256`: the raw-byte lowercase hash from `read_file` or `search_files`, or
`"missing"` for a new file. Example tool arguments:

```json
{"changes":[
  {"path":"counter.py","expected_sha256":"<64-character hash from read_file>",
   "text":"def increment(value):\n    return value + 1\n"},
  {"path":"notes.txt","expected_sha256":"missing","text":"Counter implementation updated.\n"}
]}
```

The placeholder hash must be replaced with the observed hash. `read_file` retains its
existing normalized-newline text view; its added hash describes original bytes, including
CRLF. A stale hash fails before approval. Tool arguments use a bounded object-array schema
with host validation; model-provided fields cannot expand that contract or permissions.

## Review and conflicts

Studio presents one **apply patch set** approval listing all changed files, operations,
preimage/proposed hashes, sizes and diffs. No file changes before approval. Known credential
patterns are removed from whole-file text before diff generation; affected reviews are
marked `redacted`. This does not identify every secret. Diff limits cause refusal with a
request to split the set, never a silently truncated review. Empty files are supported;
unchanged files require no mutation approval and retain readback observations.

After approval, every file's identity, metadata and bytes must still match its reviewed
preimage. A changed/deleted/recreated file or new occupant blocks the entire set before
publication starts. Pending preimages are rechecked during publication. Existing strict
path/link/hardlink guards and atomic single-file publication are reused. Private state,
credential/control paths, duplicates and overlapping destinations are refused.

## Partial outcomes and limits

Files publish sequentially. The set is **not a crash-atomic transaction**. An error or
concurrent change after the first publication can leave completed work. Results distinguish
`written_paths`, `uncertain_paths` and `pending_paths`, with per-file artifact observations.
Failed readback stops later writes. An incomplete result blocks automatic agent continuation;
inspect actual files and request a fresh review. Automatic rollback could overwrite someone
else's edit, so none is attempted. Emergency stop/process death can interrupt reporting;
completed changes remain and restart must not replay the set. Durable operation journaling
and crash reconciliation remain separate roadmap work.

Limits: 1–8 files, 64,000 total proposed UTF-8 bytes, 64,000 bytes per preimage, 32,000 bytes
of review diff. Only create/replace is supported; no deletion, rename, binary patch, shell
execution or automatic commit. Tests retain their separate execute-code approval. Artifact
hash agreement is a point-in-time observation, not proof of code correctness or OS isolation.

Run `python -m unittest tests.test_patch_sets -v` in the project environment. Enable
`LIVE_STUDIO_UI=1` for `tests.test_tool_profile_ui`. These checks execute real filesystem,
worker, test-runner and UI paths with explicit model protocol fixtures. Current live-model
acceptance remains unverified. The existing [Ollama tool protocol](https://github.com/ollama/ollama/blob/main/docs/capabilities/tool-calling.mdx)
is reused; no extra agent framework or dependency is introduced. Restart/rebuild the backend
after source changes; older release snapshots do not acquire this feature automatically.
