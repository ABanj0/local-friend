# Slash commands in Local Agent Studio

Restart Studio with ` .\desktop-dev.ps1` after this update. Type **/** in the message box
to browse commands, or click the **/** button for help. Use **↑/↓** to select, **Tab** to
insert, **Enter** to submit, **Shift+Enter** for a newline, and **Esc** to dismiss suggestions.
An incomplete command such as `/pl` is completed before submission. Command names are
case-insensitive; arguments retain their case. Unknown commands show an error and are not
sent to the model. Start with `//` to send a literal leading `/` as ordinary message text.

## Commands

| Command | Behavior |
| --- | --- |
| `/help` | Open the command catalog and usage examples; use the composer for prefix suggestions. |
| `/plan <objective>` | Generate a proposed plan, with **no tool execution**. With no objective, use the active goal. |
| `/goal <objective>` | Save a goal for this conversation and generate its initial checklist without executing it. |
| `/goal set <objective>` | Explicit creation form; useful when the objective begins with a reserved word such as “Plan” or “Run.” |
| `/goal` or `/goal status` | Show the latest goal and its reviewed checklist. |
| `/goal run [instruction]` | Start an agent task toward the active goal, including the objective and remaining checklist as context. |
| `/goal plan` | Retry generation of a missing goal checklist. Existing progress is never overwritten. |
| `/goal done N` | Mark checklist step N reviewed/done, starting at 1. |
| `/goal undo N` | Uncheck checklist step N. |
| `/goal complete` | Mark the goal completed by you, after every step is checked. |
| `/goal cancel` | End goal tracking while retaining its record. Stop its active task first. |
| `/chat <message>` | Ask the model with tools disabled, regardless of the current workspace. |
| `/agent <instruction>` | Run the existing agent with normal planning, tools and approvals. |
| `/browser <instruction>` | Run a browser task in the existing isolated browser workflow. |
| `/desktop <instruction>` | Run a desktop task using approved applications and controls. |
| `/code <instruction>` | Run a coding task in the selected approved project. |
| `/summarize [focus]` | Summarize conversation context, decisions, observed results and open work; no tools execute. |
| `/test [project]` | Run the configured `test` profile directly after approval; no inference is needed. |
| `/diff [project]` | Run the existing reviewed Git diff action; no inference is needed. Shows unstaged tracked changes, excluding staged/untracked files. |
| `/stop` | Cancel the single active task. Also queues cancellation if a task is still being created. Completed actions remain. |
| `/new [title]` | Create a fresh conversation. Existing tasks are not cancelled by switching chats. |
| `/rename <title>` | Rename this chat. |
| `/export` | Download the current conversation as Markdown. |
| `/model [name]` | Open model settings, or select an installed model by its exact name. Does not download models. |
| `/delete` | Open the existing deletion confirmation. It does not delete immediately. |
| `/remember <note>` | Save explicit text in the selected project's local memory; no inference. |
| `/recall <keywords>` | Search saved notes in the selected project, with source IDs; no inference. |
| `/forget <memory-id>` | Open the memory deletion confirmation; no immediate deletion. |

`[project]` is a workspace-relative directory; omit it to use the selected project. Names
with spaces need no shell quoting. These shortcuts never accept arbitrary shell commands.
The model still cannot change command profiles, scopes or approvals.

See [project memory scope, citations and forgetting behavior](project-memory.md).
Memory commands do not ingest pending attachments. Deleting a source chat also removes
its saved notes and excludes earlier memory-influenced context from future requests.

## Example: build a counter

```text
/plan Build a Python counter with increment, decrement, reset, and unittest tests.
/goal Build and verify a small Python counter in counter-demo.
/goal run Implement the counter and tests, then verify their behavior.
/test counter-demo
/goal status
/goal done 1
```

Review the actual checklist and tool results before checking each appropriate step, then
use `/goal complete`. The goal card provides the same Run, check/uncheck, Complete and
Cancel controls without requiring typed commands. Planning alone creates no project files.

## Goal behavior and boundaries

Goals and checklist progress are persisted in SQLite and survive an app/backend restart.
One goal may be active per conversation; complete or cancel it before creating another.
Previous goal records are retained until the conversation is deleted. The card displays
the latest goal. Creating a goal does not automatically execute its plan.

`/goal run` uses the existing bounded agent loop. It stops on completion, cancellation,
policy denial, errors, or step/context limits. You may start another run with the remaining
work as context. This is **not checkpoint pause/resume or a background scheduler**. Interrupted
tasks are not silently replayed after a restart. A goal can remain active while its task is
cancelled or blocked. No model report automatically checks steps or completes a goal.

Checklist progress is explicitly **user-reviewed**, not an independent verification claim.
The Complete control stays disabled until all steps have been checked. A goal's active task
must finish or be stopped before completing/cancelling the goal.

If initial planning fails (for example, Ollama is offline), the objective remains saved.
Fix the underlying issue and use `/goal plan` to generate its missing checklist. A standalone
`/plan`, including regeneration of its answer, remains tool-free. `/test` and `/diff` must be
rerun explicitly; the response-regeneration action does not silently rerun these commands.

Attachments keep their existing size/context/vision requirements. Plan/chat/agent commands
can consume pending attachments. Test/diff shortcuts ask you to send pending attachments
first. Pure goal status/checklist controls leave pending attachments in place. Uploaded
files, websites, model answers and tool output never dispatch slash commands.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_slash_commands -v
$env:LIVE_STUDIO_UI = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_slash_ui -v
Remove-Item Env:LIVE_STUDIO_UI
```

Backend tests cover command routing, persistence, explicit completion, cancellation lock
availability, scope/auth failures, plan-only regeneration, approved unittest execution and
real Git diffs. The browser test uses actual React, FastAPI, SQLite, worker processes and
Ollama against temporary workspaces. Only the native connection handshake is bridged to
the isolated test backend. It exercises keyboard discovery, planning/regeneration, goal
creation/run/reload/progress/completion, summaries, models, tests/diffs and both active and
queued cancellation, plus existing attachment/chat management flows.

A screenshot is saved to `workspace/studio-slash-goal-acceptance.png`. No new installer or
native desktop/browser automation acceptance is implied by these command-interface tests.
