"""Studio slash commands: explicit user input, never interpreted from model/tool output."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    usage: str
    local: bool = False


COMMANDS = [
    Command("help", "Show commands and examples", "/help", True),
    Command("plan", "Create a plan without executing tools", "/plan <objective>"),
    Command("goal", "Track an objective and checklist", "/goal [set] <objective> | status | run | plan | done N | undo N | complete | cancel"),
    Command("chat", "Ask the model without running tools", "/chat <message>"),
    Command("agent", "Execute a multi-step task with approvals", "/agent <instruction>"),
    Command("browser", "Run a browser task", "/browser <instruction>"),
    Command("desktop", "Run a desktop task", "/desktop <instruction>"),
    Command("code", "Run a coding task in the selected project", "/code <instruction>"),
    Command("summarize", "Summarize this conversation and open work", "/summarize [focus]"),
    Command("test", "Run the configured test profile after approval", "/test [workspace-relative project]"),
    Command("diff", "Review a Git diff after approval", "/diff [workspace-relative project]"),
    Command("stop", "Cancel the current task; completed actions remain", "/stop", True),
    Command("new", "Start a fresh conversation", "/new [title]", True),
    Command("rename", "Rename this conversation", "/rename <title>", True),
    Command("export", "Download this chat as Markdown", "/export", True),
    Command("model", "Open models or select an installed model", "/model [installed-model-name]", True),
    Command("delete", "Open this chat's deletion confirmation", "/delete", True),
    Command("remember", "Save an explicit note in the selected project", "/remember <note>"),
    Command("recall", "Search the selected project's saved notes", "/recall <keywords>"),
    Command("forget", "Confirm removal of a saved project note", "/forget <memory-id>", True),
]


def parse_command(text):
    text = text.strip()
    if not text.startswith("/"):
        raise ValueError("Slash commands must begin with /")
    parts = text[1:].split(maxsplit=1)
    name = parts[0].lower() if parts else ""
    command = next((item for item in COMMANDS if item.name == name), None)
    if command is None:
        raise ValueError(f"Unknown command /{name}. Type /help to see available commands.")
    return command, parts[1].strip() if len(parts) == 2 else ""


def goal_report(goal):
    if not goal:
        return "No active goal. Use /goal <objective> to create one."
    steps = "\n".join(f"{index+1}. [{'x' if step['done'] else ' '}] {step['text']}"
                      for index, step in enumerate(goal["steps"]))
    return f"Goal ({goal['status']}): {goal['objective']}\n{steps or 'Checklist not generated yet; use /goal plan.'}"


def dispatch_command(manager, body, start):
    command, argument = parse_command(body.objective)
    if command.local:
        raise ValueError(f"Use /{command.name} through the Studio composer")
    conversation = body.conversation
    manager.store.messages(conversation)  # Validate before mutating state.
    if command.name == "goal":
        pending = None
        with manager.lock:
            goal = manager.store.current_goal(conversation)
            operation = argument.split(maxsplit=1)[0].lower() if argument else "status"
            if operation == "set":
                argument = argument[3:].strip()
                operation = "create"
            if operation == "status":
                if argument.lower() not in {"", "status"}:
                    raise ValueError("Usage: /goal status")
                return {"action": "goal", "goal": goal, "notice": goal_report(goal)}
            if operation in {"done", "undo", "complete", "cancel", "plan", "run"}:
                if not goal or goal["status"] != "active":
                    raise ValueError("Create an active goal first with /goal <objective>")
                if operation in {"done", "undo"}:
                    parts = argument.split()
                    if len(parts) != 2 or not parts[1].isdigit():
                        raise ValueError(f"Usage: /goal {operation} <step number>")
                    manager.store.goal_step(conversation, int(parts[1])-1, operation == "done")
                elif operation in {"complete", "cancel"}:
                    if argument.lower() != operation:
                        raise ValueError(f"Usage: /goal {operation}")
                    if any(state.get("goal") == goal["id"] and not state["done"] for state in manager.running.values()):
                        raise ValueError("Stop or finish the goal's current task first")
                    manager.store.finish_goal(conversation, "completed" if operation == "complete" else "cancelled")
                elif operation == "plan":
                    if argument.lower() != "plan" or goal["steps"]:
                        raise ValueError("/goal plan generates a missing checklist; existing progress is preserved")
                    pending = (goal["objective"], "plan", goal["id"])
                else:
                    instruction = argument[len("run"):].strip() or "Work toward the active goal. Verify results and report completed work and remaining issues."
                    pending = (instruction, "agent", goal["id"])
                if pending is None:
                    updated = manager.store.current_goal(conversation)
                    return {"action": "goal", "goal": updated, "notice": goal_report(updated)}
            else:
                if not argument:
                    raise ValueError("Usage: /goal <objective>")
                if manager.running:
                    raise ValueError("Finish or cancel the current task before creating a goal")
                goal = manager.store.create_goal(conversation, argument)
                pending = (argument, "plan", goal["id"])
        # Preflight/model requests must not hold the cancellation/approval lock.
        return start(pending[0], pending[1], goal_id=pending[2])
    if command.name == "plan":
        if not argument:
            goal = manager.store.current_goal(conversation)
            argument = goal["objective"] if goal and goal["status"] == "active" else ""
        if not argument:
            raise ValueError("Usage: /plan <objective>, or create an active goal first")
        return start(argument, "plan")
    if command.name == "summarize":
        return start("Summarize the preceding conversation: objective, decisions, verified results and unresolved work. "
                     "Do not claim to have executed new actions. " + (f"Focus: {argument}" if argument else ""), "chat")
    if command.name in {"test", "diff"}:
        if body.attachments:
            raise ValueError("Send pending attachments before running a test/diff shortcut")
        project = argument or body.project
        return start(f"{'Run configured tests' if command.name == 'test' else 'Review Git diff'} in {project}.",
                     command.name, project=project)
    if not argument:
        raise ValueError(f"Usage: {command.usage}")
    return start(argument, {"code": "coding"}.get(command.name, command.name))
