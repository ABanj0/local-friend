import copy
import json
import math
import multiprocessing
import os
import sqlite3
import threading
import time
import uuid
from contextlib import ExitStack

from local_agent.agent import clean
from local_agent.background import accept_status as accept_background_status
from local_agent.background import readiness_config
from local_agent.captures import Captures
from local_agent.command_output import accept_event as accept_command_output
from local_agent.context import validate_notice as validate_context_notice
from local_agent.execution import recover as recover_execution
from local_agent.inference import InferenceOptions
from local_agent.observability import validate as validate_trace
from local_agent.safety import Policy, Stopped, redact
from local_agent.studio.attachments import model_message
from local_agent.studio.history import TASK_COLUMNS
from local_agent.studio.history import page as history_page
from local_agent.studio.journal import label as journal_label
from local_agent.studio.journal import scope_key as journal_scope_key
from local_agent.studio.memory import Memory
from local_agent.studio.memory import prompt as memory_prompt
from local_agent.studio.memory_admission import MODES as MEMORY_MODES
from local_agent.studio.memory_admission import prepare as prepare_memory
from local_agent.studio.memory_index import MemoryIndex
from local_agent.studio.memory_sources import UNSET, MemorySources
from local_agent.studio.state_owner import database_path
from local_agent.studio.store import Store
from local_agent.studio.worker import worker_main
from local_agent.tool_spec import categories


def _discard_startup_process(proc):
    """Reap and close only this startup's process, including a partially successful start."""
    try:
        if proc.pid is not None:
            if proc.is_alive():
                try:
                    proc.terminate()
                except OSError:
                    proc.kill()
            proc.join(2)
            if proc.is_alive():
                proc.kill()
                proc.join(2)
    finally:
        proc.close()


def _queued(pipe):
    try:
        return pipe.poll()
    except (EOFError, OSError):
        # On Windows the writer may close immediately after a valid final frame.
        # A look-ahead failure must not discard that already received result.
        return False


class Manager:
    def __init__(self, config):
        self.config = config
        recover_execution(config)
        self.store = Store(database_path(config))
        self.store.recover()
        self.capture_errors = Captures.recover(config["paths"]["state"])
        self.lock = threading.RLock()
        self.running = {}
        self.memory = Memory(self)
        self.memory_index = MemoryIndex(self)
        self.memory_sources = MemorySources(self)
        self.live_events = []
        self.sequence = 0
        self.event_epoch = uuid.uuid4().hex
        self.live_sizes = {}
        self.live_bytes = 0
        self.shutdown_requested = threading.Event()
        self.restore_pending = threading.Event()
        self.admission_epoch = 0
        self.scheduler = None
        self.limits = {"ready_timeout": 15, "heartbeat_timeout": 10,
                       "model_timeout": config["model"]["timeout"] + 15,
                       "tool_timeout": 120, "execution_timeout": 30, "task_timeout": 3600,
                       "approval_timeout": 300}
        self.limits.update(config.get("execution", {}))
        if any(type(value) not in {int, float} or not math.isfinite(value) or value <= 0
               for value in self.limits.values()) or self.limits["approval_timeout"] > 300:
            raise ValueError("Execution timeouts must be finite positive seconds; approval_timeout <= 300")

    def _publish(self, event):
        """Publish an already committed event (or an explicitly transient diagnostic)."""
        with self.lock:
            self.sequence += 1
            event["live_seq"] = self.sequence
            size = len(json.dumps(event, ensure_ascii=False).encode("utf-8"))
            self.live_events.append(event)
            self.live_sizes[self.sequence] = size
            self.live_bytes += size
            while self.live_events and (len(self.live_events) > 4000 or self.live_bytes > 16 * 1024**2):
                removed = self.live_events.pop(0)
                self.live_bytes -= self.live_sizes.pop(removed["live_seq"])
        return event

    def emit(self, task, kind, payload):
        # Streaming chunks stay in RAM; final responses are persisted as messages.
        with self.lock:
            if kind == "token":
                event = {"seq": 0, "task": task, "kind": kind, "payload": payload}
            else:
                event = self.store.event(task, kind, payload)
            return self._publish(event)

    def discard_events(self, tasks):
        with self.lock:
            self.live_events = [event for event in self.live_events if event.get("task") not in tasks]
            self.live_sizes = {event["live_seq"]: self.live_sizes[event["live_seq"]]
                               for event in self.live_events}
            self.live_bytes = sum(self.live_sizes.values())

    def start(self, conversation, objective, mode, model, project=".", settings=None, regenerate=False,
              attachment_ids=None, goal_id=None, profile="unified", *, inspection=None, resume_from=None, queue_claim=None,
              _source_preflight=UNSET):
        source_preflight = (self.memory_sources.prepare(project) if _source_preflight is UNSET else _source_preflight) if mode in MEMORY_MODES else None
        recalled_preflight = prepare_memory(self, conversation, project, objective, mode, regenerate, sources=source_preflight)
        with self.lock:
            if queue_claim is not None:
                from local_agent.studio.work_queue import Claim
                if not isinstance(queue_claim, Claim) or queue_claim.owner != self.event_epoch:
                    raise ValueError('Queue claim belongs to a different backend admission owner')
            if (mode == 'inspection') != (inspection is not None):
                raise ValueError('Use the dedicated selected-file inspection interface')
            if inspection is not None and (regenerate or attachment_ids or goal_id):
                raise ValueError('Inspections do not accept regeneration, attachments or tracked goals')
            if self.shutdown_requested.is_set():
                raise OSError("Backend is shutting down")
            if self.restore_pending.is_set():
                raise ValueError('Restore requires a backend restart before starting tasks')
            if self.running:
                raise ValueError("Another task is active; finish or cancel it first")
            if self.memory_index.busy:
                raise ValueError("A memory embedding operation is active; wait before starting a task")
            if self.capture_errors:
                self.capture_errors = Captures.recover(self.config["paths"]["state"])
                if self.capture_errors:
                    raise OSError("Owned screenshot cleanup needs attention; inspect the capture registry")
            # Forgetting excludes old model context, while preserving the visible transcript.
            history = self.store.messages(conversation, for_model=True)
            attachment_ids = attachment_ids or []
            if regenerate and attachment_ids:
                raise ValueError("Send new attachments in a new message")
            if regenerate:
                original_task = self.store.latest_task(conversation)
                if original_task:
                    profile = original_task.get("profile", "unified")
                    if original_task["mode"] in {"test", "diff", "inspection"}:
                        raise ValueError("Rerun tool shortcuts or selected-file inspections through their dedicated controls")
                    mode = original_task["mode"]  # Regenerating a plan must never execute it.
                previous = next((i for i in range(len(history) - 1, -1, -1) if history[i]["role"] == "user"), None)
                if previous is None:
                    raise ValueError("No user message to regenerate")
                objective = history[previous]["content"]
                attachments = self.store.attachments(conversation, message=history[previous]["id"], include_data=True)
                history = history[:previous]
            else:
                attachments = self.store.attachments(conversation, ids=attachment_ids, pending=True, include_data=True)
            if not objective.strip():
                raise ValueError("Enter a message")
            if mode in {"test", "diff", "inspection"}:
                if attachment_ids:
                    raise ValueError("Tool shortcuts do not accept attachments")
                history = []  # Deterministic tools need no model context or image data.
            allowed_categories = categories(profile)
            if mode in {"test", "diff"} and "coding" not in allowed_categories:
                raise ValueError("This shortcut requires a profile with coding tools")
            config = copy.deepcopy(self.config)
            config["_tool_profile"] = profile
            config["execution"] = dict(self.limits)
            root = Policy(config).path(project)
            if not root.is_dir():
                raise ValueError("Select an existing project directory")
            config["paths"]["workspace"] = str(root)
            recalled = self.memory.retrieve(conversation, project, objective, prepared=recalled_preflight,
                                           sources=source_preflight) if mode not in {"test", "diff", "inspection"} else []
            if mode in {"test", "diff", "inspection"}:
                with self.store.connection() as db:
                    self.memory.bind(db, conversation, journal_scope_key(root))
            config["model"]["name"] = model
            if settings and set(settings) - set(InferenceOptions.__dataclass_fields__):
                raise ValueError("Unknown inference setting; endpoint and execution limits cannot be overridden")
            config["model"].update(settings or {})
            InferenceOptions.from_config(config["model"])
            if inspection is not None:
                from local_agent.studio.inspection import current, validate_agent
                _, contents = current(self, inspection['spec'])
                if inspection['agent'] is not None:
                    validate_agent(inspection['agent'], inspection['spec'], contents)
                config['_inspection'] = copy.deepcopy(inspection)
            # Only the GUI service sets these; a tool cannot expand allowed scope.
            config["browser"]["headless"] = False if mode == "browser" else config["browser"]["headless"]
            history = [model_message(m["content"], self.store.attachments(
                conversation, message=m["id"], include_data=True)) if m["role"] == "user"
                else {"role": m["role"], "content": m["content"]} for m in history]
            current_message = model_message(objective, attachments)
            current_message["content"] += memory_prompt(recalled)
            goal = self.store.current_goal(conversation)
            if goal_id and (not goal or goal["id"] != goal_id or goal["status"] != "active"):
                raise ValueError("The goal changed before the task started; review its current status")
            if goal and goal["status"] == "active" and mode in {"agent", "browser", "desktop", "coding"}:
                goal_id = goal["id"]
                with self.store.connection() as db:
                    epoch = db.execute("SELECT memory_epoch FROM conversations WHERE id=?", (conversation,)).fetchone()[0]
                remaining = [step["text"] for step in goal["steps"] if not step["done"]] if goal["memory_epoch"] == epoch else []
                current_message["content"] += (f"\nUser's tracked goal: {goal['objective']}\n"
                                               f"Remaining checklist: {remaining}\n"
                                               "Checklist marks are user-reported; verify results. Scope and approval rules still apply.")
            if sum(len(m.get("images", [])) for m in [*history, current_message]) > 8:
                raise ValueError("This conversation has too many images; start a new conversation")
            project_label = journal_label(root.relative_to(Policy(self.config).root).as_posix(), project=True)
            task = self.store.task(conversation, mode, model, goal_id, profile,
                                   project=project_label, scope_key=journal_scope_key(root),
                                   memory_refs=[record["id"] for record in recalled],
                                   **({'inspection': inspection, 'resume_from': resume_from} if inspection is not None else {}),
                                   **({'queue_claim': queue_claim} if queue_claim is not None else {}))
            config["_trace_run_id"] = task
            phase = "saving the user message"
            try:
                with ExitStack() as startup:
                    if not regenerate:
                        self.store.message(conversation, "user", objective, attachment_ids=attachment_ids)
                    captures = None
                    if mode in {"agent", "browser", "desktop", "coding"}:
                        phase = "registering screenshot ownership"
                        captures = Captures(config["paths"]["state"])
                        startup.callback(captures.close)
                        config["_capture_run"] = captures.run
                    phase = "creating the worker"
                    context = multiprocessing.get_context("spawn")
                    parent, child = context.Pipe()
                    startup.callback(parent.close)
                    startup.callback(child.close)
                    proc = context.Process(target=worker_main, args=(child, config, mode, objective, history, current_message))
                    startup.callback(_discard_startup_process, proc)
                    phase = "starting the worker"
                    proc.start()
                    child.close()
                    job = None
                    phase = "establishing the cancellation boundary"
                    if os.name == "nt":
                        from local_agent.windows_job import WindowsJob
                        # multiprocessing exposes a process handle as its Windows sentinel.
                        class Handle:
                            _handle = proc.sentinel
                        job = WindowsJob(Handle())
                        startup.callback(job.close)
                    now = time.monotonic()
                    state = {"process": proc, "pipe": parent, "job": job, "captures": captures, "worker_pid": proc.pid,
                                          "conversation": conversation, "approvals": {}, "done": False,
                                          "stream": "", "goal": goal_id, "ready": False,
                                          "heartbeat": now, "phase": "starting",
                                          "deadline": now + self.limits["ready_timeout"],
                                          "task_deadline": now + self.limits["task_timeout"],
                                          "persist_error": None}
                    if inspection is not None:
                        state['inspection'] = inspection
                    self.running[task] = state
                    phase = "publishing startup"
                    self.emit(task, "started", {"mode": mode, "model": model, "project": project, "profile": profile})
                    phase = "starting the monitor"
                    threading.Thread(target=self._monitor, args=(task, state), daemon=True).start()
                    # Release execution only after ownership, notification and monitoring exist.
                    phase = "releasing the worker"
                    parent.send("start")
                    startup.pop_all()  # The monitor now owns the process, pipe and Job Object.
            except BaseException as exc:
                # ExitStack attempts every owned cleanup even if one callback raises.
                # This lock prevents the monitor from reading state until rollback completes.
                self.running.pop(task, None)
                result = {"status": "failed", "report":
                          f"Task startup failed while {phase}: {type(exc).__name__}: {redact(str(exc))[:1000]}"}
                try:
                    event = self.store.complete(task, result)
                    if event:
                        self._publish(event)
                except (sqlite3.Error, OSError):
                    # No worker is left alive. Retain only the uncommitted outcome for retry.
                    pending = {"done": True, "terminal": result, "approvals": {}, "stream": "",
                               "conversation": conversation, "persist_error": "Completion storage unavailable"}
                    self.running[task] = pending
                    threading.Thread(target=self._save_terminal, args=(task, pending), daemon=True).start()
                if not isinstance(exc, Exception):
                    raise  # Preserve interrupts after compensating their startup state.
                raise OSError(result["report"]) from None
            return task

    def _finish(self, state, result):
        if state["done"]:
            return  # Cancellation and result race under the same lock; first outcome wins.
        if (isinstance(result, dict) and result.get('status') == 'interrupted'
                and state.get('inspection') and state.get('pause_ack')):
            result = {'status': 'interrupted', 'report': 'Read-only inspection paused at an acknowledged completed step. Resume explicitly after reviewing unchanged inputs.'}
        elif not isinstance(result, dict) or result.get("status") not in {
            "reported", "planned", "no_actions", "blocked", "failed", "cancelled"
        }:
            raise ValueError("Worker returned an invalid terminal outcome")
        state["terminal"] = clean(result)
        state["approvals"].clear()
        state["done"] = True

    def _save_terminal(self, task, state):
        # Retry persistence only. Never retry a worker, tool or approval delivery.
        while True:
            with self.lock:
                try:
                    event = self.store.complete(task, state["terminal"])
                    if event:
                        self._publish(event)
                    self.running.pop(task, None)
                    return
                except (sqlite3.Error, OSError) as exc:
                    if not state["persist_error"]:
                        self._publish({"seq": 0, "task": task, "kind": "persistence_error", "payload": {
                            "text": "Worker stopped. Final outcome is waiting for local storage recovery."}})
                    state["persist_error"] = f"{type(exc).__name__}: {redact(str(exc))[:1000]}"
                    if self.shutdown_requested.is_set():
                        self.running.pop(task, None)
                        return  # Next startup reconciles the uncommitted task as interrupted.
                except Exception as exc:  # noqa: BLE001 -- malformed terminal data must not strand a task
                    state["terminal"] = {"status": "failed", "report":
                        f"Completion failed: {type(exc).__name__}: {redact(str(exc))[:1000]}"}
            self.shutdown_requested.wait(0.1)

    def _phase(self, state, phase):
        if phase not in {"model", "tool", "execution"}:
            raise ValueError("Invalid worker phase")
        state["phase"] = phase
        state["deadline"] = time.monotonic() + self.limits[phase + "_timeout"]

    def _check_deadline(self, state, *, heartbeat=True):
        now = time.monotonic()
        if heartbeat and state["ready"] and now - state["heartbeat"] > self.limits["heartbeat_timeout"]:
            raise TimeoutError("Worker heartbeat lost; task stopped without replay")
        if state["approvals"]:
            if any(request["expires"] <= time.time() for request in state["approvals"].values()):
                self._finish(state, {"status": "blocked", "report": "Approval expired; task stopped without replay."})
        else:
            if now > state["task_deadline"]:
                raise TimeoutError("Worker task deadline exceeded; task stopped without replay")
            if now > state["deadline"]:
                raise TimeoutError(f"Worker {state['phase']} deadline exceeded; task stopped without replay")

    def _terminate(self, state):
        """Best-effort independent stop paths; a failed Job call must not skip process kill."""
        if state.get("job"):
            try:
                state["job"].terminate()
            except OSError:
                try:
                    state["job"].close()  # KILL_ON_JOB_CLOSE includes owned descendants.
                except OSError:
                    pass  # Also attempt the process fallback below and close again in cleanup.
        proc = state.get("process")
        if proc is not None and not state.get("process_closed") and proc.is_alive():
            try:
                proc.terminate()
            except OSError:
                try:
                    proc.kill()
                except OSError as exc:
                    state["cleanup_error"] = redact(str(exc))[:1000]

    def _cleanup(self, state):
        proc = state["process"]
        while True:
            try:
                # Serialize handle closure with cancel/approval delivery; a closed Process
                # must never be inspected by a simultaneous stop request.
                with self.lock:
                    self._terminate(state)
                    if not state.get("process_closed"):
                        proc.join(0.2)
                        if proc.is_alive():
                            proc.kill()
                            proc.join(0.2)
                    if state["job"]:
                        state["job"].close()
                    state["pipe"].close()
                    if not state.get("process_closed"):
                        proc.close()
                        state["process_closed"] = True
                    if state.get("captures"):
                        state["captures"].close()
                recover_execution(self.config, state.get("worker_pid"))
                with self.lock:
                    state.pop("cleanup_error", None)
                    return
            except Exception as exc:  # noqa: BLE001 -- retain ownership until every resource is closed
                state["cleanup_error"] = f"{type(exc).__name__}: {redact(str(exc))[:1000]}"
                time.sleep(0.1)

    def _monitor(self, task, state):
        with self.lock:
            if self.running.get(task) is not state:
                return  # Startup rolled back after the monitor thread was created.
        proc, pipe = state["process"], state["pipe"]
        try:
            while not state["done"]:
                if pipe.poll(0.1):
                    event = pipe.recv()
                    with self.lock:
                        if state["done"]:
                            break
                        kind, payload = event["kind"], event["payload"]
                        if kind not in {"worker_ready", "heartbeat", "phase", "token", "tool_start",
                                        "tool_result", "approval", "result", "progress", "plan", "preview", "verification", "command_output", "background_status", "trace", "operation_intent", "operation_result", "context", "inspection_checkpoint"} or not isinstance(payload, dict):
                            raise ValueError("Invalid worker event payload")
                        if kind == "heartbeat":
                            state["heartbeat"] = time.monotonic()
                        # Drain queued liveness frames before declaring a missing heartbeat.
                        # Model/tool/task budgets still apply even while data keeps arriving.
                        self._check_deadline(state, heartbeat=kind == "heartbeat" or not _queued(pipe))
                        if state["done"]:
                            break
                        if kind == "worker_ready":
                            state["ready"] = True
                            state["heartbeat"] = time.monotonic()
                            self._phase(state, "execution")
                        if kind == "heartbeat":
                            continue
                        if kind == "phase":
                            if not state["ready"]:
                                raise ValueError("Worker sent a phase before readiness")
                            self._phase(state, payload["name"])
                        if kind == "token":
                            state["stream"] += payload["text"]
                        if kind == "context":
                            payload = validate_context_notice(payload)
                        if kind == "tool_start":
                            self._phase(state, "tool")
                        if kind == "trace":
                            payload = validate_trace(payload, task, state.setdefault("trace_spans", {}))
                            if payload["verification_ids"]:
                                ids = payload["verification_ids"]
                                with self.store.connection() as db:
                                    count = db.execute("SELECT count(*) FROM verifications WHERE task=? AND id IN ("
                                                       + ",".join("?" for _ in ids) + ")", [task, *ids]).fetchone()[0]
                                if count != len(ids):
                                    raise ValueError("Trace references unknown verifier evidence")
                            if payload["kind"] == "step":
                                event = self.store.record_step(task, payload)
                                if event:
                                    self._publish(event)
                                continue
                        if kind == "operation_intent":
                            spans = state.get("trace_spans", {})
                            call, step = spans.get(payload.get("id"), {}), spans.get(payload.get("step"), {})
                            if (state.get("operation") or call.get("kind") != "tool" or call.get("phase") != "started"
                                    or call.get("parent") != payload.get("step") or call.get("tool") != payload.get("tool")
                                    or step.get("kind") != "step" or step.get("phase") != "started"):
                                raise ValueError("Operation has no active trace decision/tool")
                            event = self.store.operation_intent(task, payload)
                            if event is None:
                                raise ValueError("Operation intent was not committed")
                            self._publish(event)
                            state["operation"] = payload["id"]
                            pipe.send({"id": payload["id"], "journal_ack": "intent"})
                            continue
                        if kind == "operation_result":
                            if state.get("operation") != payload.get("id"):
                                raise ValueError("Unexpected operation result")
                            event = self.store.operation_result(task, payload)
                            if event is None:
                                raise ValueError("Operation result was not committed")
                            self._publish(event)
                            state["operation"] = None
                            pipe.send({"id": payload["id"], "journal_ack": "result"})
                            continue
                        if kind == 'inspection_checkpoint':
                            from local_agent.studio.inspection import current, validate_agent
                            if not state.get('inspection') or state.get('operation') or state['approvals']:
                                raise ValueError('No supported inspection boundary')
                            spec = state['inspection']['spec']
                            _, contents = current(self, spec)
                            validate_agent(payload, spec, contents)
                            event = self.store.inspection_checkpoint(task, payload, paused=bool(state.get('pause_requested')))
                            self._publish(event)
                            state['pause_ack'] = event['payload']['pause_acknowledged']
                            pipe.send({'checkpoint_ack': payload['next_step'], 'pause': state['pause_ack']})
                            continue
                        if kind == "command_output":
                            if payload.get("profile") not in self.config["commands"]:
                                raise ValueError("Unknown command output profile")
                            accept_command_output(payload, state.setdefault("command_outputs", {}))
                        if kind == "background_status":
                            profile = payload.get("profile")
                            if not isinstance(profile, str) or profile not in self.config["commands"]:
                                raise ValueError("Unknown background status profile")
                            settings = readiness_config(self.config.get("readiness", {}).get(profile))
                            accept_background_status(payload, self.config["commands"], settings,
                                state.get("command_outputs", {}), state.setdefault("background_updates", {}))
                        if kind == "approval":
                            if state.get('inspection'):
                                raise ValueError('Read-only inspections cannot request tool approval')
                            if (not isinstance(payload.get("id"), str) or payload["id"] in state["approvals"]
                                or type(payload.get("expires")) not in {int, float}
                                or not math.isfinite(payload["expires"])
                                or not time.time() < payload["expires"] <= time.time() + 301):
                                raise ValueError("Invalid approval request")
                            if not state["approvals"]:
                                state["approval_started"] = time.monotonic()
                            state["approvals"][payload["id"]] = payload
                            self.store.waiting(task, True)
                        if kind == "result":
                            self._finish(state, payload)
                            break  # Result publication belongs to the completion transaction.
                        if kind == "verification":
                            event = self.store.verification(task, payload)
                            if event:
                                self._publish(event)
                            continue  # Evidence row and its event were committed together.
                        self.emit(task, kind, payload)
                elif not proc.is_alive():
                    break
                with self.lock:
                    if not state["done"]:
                        self._check_deadline(state, heartbeat=not _queued(pipe))
            with self.lock:
                if not state["done"]:
                    result = {"status": "failed", "report": "Worker exited unexpectedly; no task was replayed."}
                    self._finish(state, result)
        except Stopped:
            with self.lock:
                self._finish(state, {'status': 'cancelled', 'report': 'Inspection interrupted by emergency stop.'})
        except Exception as exc:  # noqa: BLE001 -- monitor failures must still stop/reconcile the worker
            with self.lock:
                self._finish(state, {"status": "failed", "report":
                    f"Worker supervision failed: {type(exc).__name__}: {redact(str(exc))[:1000]}"})
        finally:
            try:
                self._cleanup(state)
            finally:
                self._save_terminal(task, state)

    def approve(self, task, ident, approved):
        with self.lock:
            state = self.running.get(task)
            if not state or state["done"]:
                raise ValueError("Task is no longer active")
            request = state["approvals"].get(ident)
            if not request or request["expires"] < time.time():
                raise ValueError("Approval expired or was already answered")
            state["approvals"].pop(ident)
            try:
                state["pipe"].send({"id": ident, "approved": approved})
                if not state["approvals"]:
                    waited = time.monotonic() - state["approval_started"]
                    state["deadline"] += waited
                    state["task_deadline"] += waited
                    self.store.waiting(task, False)
                self.emit(task, "approval_resolved", {"id": ident, "approved": approved})
            except Exception as exc:  # noqa: BLE001 -- never leave an approval-delivery failure active
                self._finish(state, {"status": "failed", "report":
                    f"Approval handling failed: {type(exc).__name__}: {redact(str(exc))[:1000]}. "
                    "Completed actions were not undone."})
                self._terminate(state)
                raise OSError("Approval handling failed; task stopped. Completed actions were not undone.") from None

    def cancel(self, task):
        with self.lock:
            state = self.running.get(task)
            if not state or state["done"]:
                return
            result = {"status": "cancelled", "report": "Cancelled. Completed actions were not undone."}
            self._finish(state, result)
            self._terminate(state)

    def pending(self):
        with self.lock:
            return [{"task": task, **request} for task, state in self.running.items()
                    for request in state["approvals"].values() if request["expires"] > time.time()]

    def diagnostics(self):
        with self.lock:
            errors = [{"task": task, "phase": "storage" if state.get("persist_error") else "cleanup",
                       "text": "Task stopped; waiting for local storage or owned resource cleanup."}
                      for task, state in self.running.items()
                      if state.get("persist_error") or state.get("cleanup_error")]
            return {"ready": not errors and not self.capture_errors and not self.shutdown_requested.is_set()
                    and not self.restore_pending.is_set(),
                    "task_errors": errors, "capture_cleanup_pending": bool(self.capture_errors)}

    def tasks(self):
        with self.lock:
            return self._task_runtime(self.store.tasks())

    def _task_runtime(self, rows):
        for row in rows:
            state = self.running.get(row['id'])
            if state and state['done']:
                row['runtime_state'] = 'storage' if state.get('persist_error') else 'cleanup'
        return rows

    def task_metadata(self, task):
        with self.lock, self.store.connection() as db:
            row = db.execute(f'SELECT {TASK_COLUMNS} FROM tasks WHERE id=?', (task,)).fetchone()
            if row is None:
                raise KeyError('Task not found')
            return self._task_runtime([dict(row)])[0]

    def activity_tasks(self):
        """Bounded metadata, always including every currently owned worker slot."""
        with self.lock:
            rows = history_page(self.store, 'tasks', limit=50)['items']
            seen = {row['id'] for row in rows}
            rows.extend(self.task_metadata(task) for task in self.running if task not in seen)
            return self._task_runtime(rows)

    def close(self, *, shutdown=False):
        with self.lock:
            self.admission_epoch += 1  # Invalidate selected-file admissions waiting on metadata.
            self.memory_index.cancel()
            if self.scheduler:
                self.scheduler.abort.set()
                if not shutdown:
                    self.scheduler.latched = True
            if shutdown:
                self.shutdown_requested.set()
        try:
            if self.scheduler:
                if shutdown:
                    self.scheduler.stop()
                else:
                    self.scheduler.set_paused(True)
        finally:
            for task in list(self.running):
                self.cancel(task)
        deadline = time.monotonic() + 5
        while self.running and time.monotonic() < deadline:
            time.sleep(0.05)
