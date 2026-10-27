# Tool contracts and capability profiles

Choose **Tool access** in Agent, Browser, Desktop or Workspace before submitting a task.
The default is Unified. The selector is disabled while a task is running. Profiles select
agent tools; configured paths, origins, applications, commands and action approvals still
apply to every selected tool.

| Profile | Available categories |
| --- | --- |
| `unified` | Coding, browser and desktop (22 built-in tools) |
| `coding` | Files, bounded text search, reviewed edits, Git, configured commands and owned background commands |
| `browser` | Browser navigation, reading, actions, downloads, screenshots and intervention |
| `desktop` | Approved application launch, accessibility, input and screenshots |

For example, Browser-only tasks cannot call `write_file` or execute `/test`. Browser
downloads remain browser actions and retain their destination/approval checks. Coding-only
tasks cannot launch a browser. Use Unified for workflows that combine categories.

The CLI supports the same profiles:

```powershell
.\launch.ps1 "Inspect the repository and run its tests" -Profile coding
.\.venv\Scripts\python.exe -m local_agent run "Read the allowed webpage" --profile browser
```

Authenticated `/tasks` and `/slash` requests accept `profile`. Task history and the started
event record the selected value. Regeneration reuses the original task's profile; changing
the selector cannot widen a regenerated task. Submit a new request to choose different
access. Existing tasks migrate to Unified. A profile is per run and does not grant new
filesystem/network scope or operating-system isolation. User-operated workspace inspection
remains separately subject to the existing API path checks.

## Built-in tool contracts

`local_agent/tool_spec.py` defines frozen version-1 `ToolSpec` and `ArgumentSpec` records.
Each names its category, handler, description, signature and typed arguments. Defaults
are applied by validation; the original 19 model-facing JSON schemas are preserved.
`search_files` adds [bounded repository text search](repository-search.md) as the twentieth tool.
`apply_patch` adds [reviewed related-file changes](patch-sets.md) as the twenty-first tool,
with a bounded, explicitly typed object-array contract. Existing 20 schemas are preserved.
`command_status` adds [owned background status/readiness](background-commands.md) as the
twenty-second tool; the preceding 21 schemas are preserved. It cannot inspect unrelated
processes or accept model-supplied probe URLs.
Extra/missing arguments, incorrect scalar types (including bool instead of integer),
unknown command names and tools outside the selected profile fail before adapter dispatch.
Errors retain the existing normalized result shape and content-free audit logging.

Registration is trusted host code in `local_agent/tools.py`. To extend it, implement an
adapter with explicit scope/approval checks, add its registration and category deliberately,
then add contract, denial and integration tests. The registry is read-only after creation;
model text, repository content and tool results cannot register providers or choose profiles.
MCP support remains a later roadmap increment. No additional framework is required here.

Restart the backend after updating Python source and rebuild the frontend for the selector.
Previously built release artifacts contain their recorded source snapshot and require a
new packaging build to include subsequent roadmap changes.

## Current model validation limitation

The 2026-10-23 managed Ollama launch reported Access is denied opening the existing model
manifest. Contract tests and real local browser/approved-test UI checks pass; new live-model
regression is blocked. Start `scripts/start-model.ps1` in a normal Windows session and check
`(Invoke-RestMethod http://127.0.0.1:11434/api/tags).models.name` includes the configured model
before rerunning the opt-ins in IMPLEMENTATION.md. The manifest warning alone does not prove
the stored model is corrupt. No model deletion or permission change was performed.
