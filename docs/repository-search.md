# Scoped repository search

Open **Workspace**, choose a project inside the configured workspace, and enter text in
**Search project text**. Search is literal and case-sensitive; regex and shell commands
are not accepted. Click a result to open its file. Results show the relative path, original
line/column, a bounded sanitized preview, and whether the searched scope was incomplete.
The file viewer uses the existing approved-file policy. Reopening reads current contents;
a search result is a point-in-time observation and does not lock a file against edits.

Coding and Unified agent profiles also expose `search_files`, for example:

```json
{"query":"def increment", "path":"counter-project", "limit":10}
```

Agent paths are relative to the selected task project; Workspace paths are relative to
the configured workspace. The authenticated read-only API is
`GET /search?query=increment&project=counter-project&limit=10`. Existing localhost/token
protection applies. Search neither executes project code nor changes files or approvals.

## Scope and limits

- UTF-8 regular files only; binary, invalid UTF-8, credential/control paths, links/reparse
  points, dependency/build descendants and the configured agent state directory are excluded.
  This is not a repository-wide completeness or secret-detection guarantee.
- Query: 1–256 characters on one line. At most 100 matching lines (default 50), one match
  per line, with 240-character previews. Each result includes the observed file's SHA-256.
- Traversal: 10,000 entries, 500 attempted eligible files, 8 MiB read, 64,000 bytes per
  file, 20 directory levels, three seconds checked between operations. Serialized results
  are bounded to 8 KiB; the output limit can precede the requested match count.
- Unreadable, oversized, changed or depth-skipped inputs make coverage incomplete. Limits
  report a stop reason. No matches means none in the eligible searched scope, not absence
  throughout the repository. Traversal order follows the filesystem and is not ranked.

Search reuses path/link guards, emergency stop and credential-pattern redaction. File
identity/size/mtime are checked before and after reading; changed inputs are omitted.
Previews redact the whole file before clipping, including supported multiline secrets.
Unknown credential formats may remain visible. Query text is not included in results;
agent audit records hash arguments and production HTTP access logging stays disabled.
These are logical policy checks, not OS isolation against hostile concurrent processes.
A blocked OS file operation can exceed the cooperative time limit; worker supervision
remains the outer cancellation boundary for agent execution.

Restart the backend and rebuild the frontend after updating source. Existing release EXEs
contain their recorded snapshots and need a new packaging build for this feature.

Run `python -m unittest tests.test_repository_search tests.test_tool_spec -v` in the project
environment. Set `LIVE_STUDIO_UI=1` to enable `tests.test_tool_profile_ui`; it uses a real
backend/browser and explicit model protocol fixtures, not live-model quality validation.
