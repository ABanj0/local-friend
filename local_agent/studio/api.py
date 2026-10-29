import asyncio
import base64
import importlib.util
import io
import secrets
import shutil
import sqlite3
import subprocess
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from local_agent.agent import clean
from local_agent.coding import Coding
from local_agent.embeddings import EmbeddingError
from local_agent.inference import InferenceOptions
from local_agent.model import Ollama
from local_agent.safety import Denied, Policy, Stopped, redact
from local_agent.studio.attachments import MAX_UPLOAD, parse_attachment
from local_agent.studio.backups import create as create_backup
from local_agent.studio.backups import inspect as inspect_backup
from local_agent.studio.backups import inventory as backup_inventory
from local_agent.studio.commands import COMMANDS, dispatch_command, parse_command
from local_agent.studio.event_stream import EventStream
from local_agent.studio.history import export_markdown
from local_agent.studio.history import page as history_page
from local_agent.studio.inspection import pause as pause_inspection
from local_agent.studio.inspection import resume as resume_inspection
from local_agent.studio.inspection import start as start_inspection
from local_agent.studio.inspection import summary as inspection_summary
from local_agent.studio.journal import inspect_operation
from local_agent.studio.manager import Manager
from local_agent.studio.memory_admission import MODES as MEMORY_MODES
from local_agent.studio.memory_sources import UNSET
from local_agent.studio.ollama_runtime import launch as ollama_launch
from local_agent.studio.process_output import ProcessOutput
from local_agent.studio.restore_activation import activate as activate_restore
from local_agent.studio.restore_gate import RestoreGate
from local_agent.studio.restores import prepare as prepare_restore
from local_agent.studio.retention import Retention
from local_agent.studio.schedules import Scheduler
from local_agent.studio.state_owner import StateOwner, read_pointer

ORIGINS = ["http://localhost:1420", "http://127.0.0.1:1420", "http://tauri.localhost", "tauri://localhost"]


class ConversationBody(BaseModel):
    title: str = Field(default="New conversation", max_length=120)


class InferenceBody(BaseModel):
    context: int = Field(default=8192, ge=2048, le=32768, strict=True)
    temperature: float = Field(default=0.1, ge=0, le=2, strict=True, allow_inf_nan=False)
    max_output: int = Field(default=2048, ge=1, le=32768, strict=True)
    thinking: StrictBool | StrictStr | None = False
    keep_alive: StrictStr | StrictInt = "5m"

    @model_validator(mode="after")
    def validate_options(self):
        options = InferenceOptions.from_config(self.model_dump())
        self.thinking = options.thinking
        return self


class TaskBody(InferenceBody):
    conversation: str
    objective: str = Field(default="", max_length=24000)
    mode: str = Field(default="chat", pattern="^(chat|agent|browser|desktop|coding|plan|test|diff)$")
    model: str = Field(min_length=1, max_length=200)
    project: str = "."
    profile: str = Field(default="unified", pattern="^(unified|coding|browser|desktop)$")
    regenerate: bool = False
    attachments: list[str] = Field(default_factory=list, max_length=4)


class ConfirmationBody(BaseModel):
    confirmed: bool = False


class MemoryIndexBody(BaseModel):
    model_config = {'extra': 'forbid'}
    project: str = Field(default='.', max_length=1000, strict=True)
    model: str = Field(min_length=1, max_length=200, strict=True)
    confirmed: StrictBool


class MemoryEnabledBody(BaseModel):
    model_config = {'extra': 'forbid'}
    project: str = Field(default='.', max_length=1000, strict=True)
    enabled: StrictBool
    confirmed: StrictBool = False


class MemorySourcePreviewBody(BaseModel):
    model_config = {'extra': 'forbid'}
    project: str = Field(default='.', max_length=1000, strict=True)
    path: str = Field(min_length=1, max_length=240, strict=True)


class MemorySourceBody(MemorySourcePreviewBody):
    conversation: str = Field(min_length=1, max_length=128, strict=True)
    sha256: str = Field(pattern='^[0-9a-f]{64}$', strict=True)
    version: str = Field(pattern='^[0-9a-f]{64}$', strict=True)
    expected_generation: str | None = Field(default=None, pattern='^[0-9a-f]{32}$', strict=True)
    confirmed: StrictBool


class MemorySourceCheckBody(BaseModel):
    model_config = {'extra': 'forbid'}
    project: str = Field(default='.', max_length=1000, strict=True)


class MemorySourceForgetBody(MemorySourceCheckBody):
    confirmed: StrictBool


class InspectionBody(InferenceBody):
    model_config = {'extra': 'forbid'}
    conversation: StrictStr
    objective: str = Field(min_length=1, max_length=12000, strict=True)
    model: str = Field(min_length=1, max_length=200, strict=True)
    project: StrictStr = '.'
    files: list[StrictStr] = Field(min_length=1, max_length=8)


class EmptyBody(BaseModel):
    model_config = {'extra': 'forbid'}


class ScheduleBody(InspectionBody):
    interval_ms: int = Field(ge=60000, le=2592000000, strict=True)
    misfire: StrictStr = Field(pattern='^(skip|coalesce)$')
    timezone: StrictStr = Field(min_length=1, max_length=100)


class ScheduleEnabledBody(EmptyBody):
    enabled: StrictBool


class DirectoryWatchBody(InspectionBody):
    directory: str = Field(default='.', max_length=240, strict=True)
    debounce_ms: int = Field(default=3000, ge=1000, le=60000, strict=True)


class SchedulerPauseBody(EmptyBody):
    paused: StrictBool
    confirmed: StrictBool = False


class ApprovalBody(BaseModel):
    approved: bool


class BackupBody(BaseModel):
    model_config = {'extra': 'forbid'}
    confirmed: StrictBool = False


class RestorePreparationBody(BackupBody):
    backup: str = Field(pattern=r'^[0-9a-f]{32}$', strict=True)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$', strict=True)


class RestoreActivationBody(BackupBody):
    preparation: str = Field(pattern=r'^[0-9a-f]{32}$', strict=True)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$', strict=True)


class RetentionPolicyBody(BaseModel):
    model_config = {'extra': 'forbid'}
    older_than_days: int = Field(default=90, ge=1, le=3650, strict=True)
    keep_recent: int = Field(default=50, ge=0, le=5000, strict=True)
    batch_size: int = Field(default=20, ge=1, le=50, strict=True)


class RetentionPreviewBody(BaseModel):
    model_config = {'extra': 'forbid'}
    protected: list[StrictStr] = Field(default_factory=list, max_length=10)


class RetentionApplyBody(BackupBody):
    preview: str = Field(pattern=r'^[0-9a-f]{32}$', strict=True)


class ProjectBody(BaseModel):
    path: str


class MemoryBody(BaseModel):
    conversation: str
    project: str = Field(default=".", max_length=1000)
    text: str | None = Field(default=None, max_length=4000)
    message: str | None = Field(default=None, max_length=32)


class ForgetBody(BaseModel):
    project: str = Field(default=".", max_length=1000)
    confirmed: StrictBool = False


class PreferencesBody(InferenceBody):
    model: str = Field(max_length=200)


def create_app(config, token, manager=None):
    if len(token) < 32:
        raise ValueError("A strong launch credential is required")
    owner = StateOwner(config)
    try:
        manager = manager or Manager(config)
    except BaseException:
        owner.close()
        raise
    restore_gate = RestoreGate()
    scheduler = Scheduler(manager, restore_gate)
    manager.scheduler = scheduler
    retention = Retention(manager)
    owned_model = ProcessOutput()
    model_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app):
        scheduler.start()
        try:
            yield
        finally:
            try:
                manager.close(shutdown=True)
            finally:
                with model_lock:
                    owned_model.close()
                if not manager.running and not (scheduler.thread and scheduler.thread.is_alive()):
                    owner.close()

    async def authorize(request: Request):
        if request.headers.get("origin") not in [None, *ORIGINS]:
            raise HTTPException(403, "Origin is not allowed")
        if not secrets.compare_digest(request.headers.get("authorization", ""), "Bearer " + token):
            raise HTTPException(401, "Invalid desktop session")

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.manager = manager
    manager.memory_index.forbidden = (token,)
    app.state.state_owner = owner
    app.state.restore_gate = restore_gate
    app.state.retention = retention
    app.state.scheduler = scheduler
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def authentication(request, call_next):
        if request.method != "OPTIONS":
            try:
                await authorize(request)
            except HTTPException as exc:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
            if request.url.path == '/health':
                return await call_next(request)
            if not restore_gate.enter():
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=409, content={'detail': 'Studio restore requires backend restart; retry after reconnecting'})
            try:
                return await call_next(request)
            finally:
                restore_gate.leave()
        return await call_next(request)

    @app.exception_handler(EmbeddingError)
    @app.exception_handler(OSError)
    @app.exception_handler(sqlite3.Error)
    async def service_error(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"detail": redact(str(exc))})

    @app.exception_handler(Denied)
    async def denied(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": redact(str(exc))})

    @app.exception_handler(ValueError)
    async def bad_value(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": redact(str(exc))})

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Resource not found"})

    @app.get("/health")
    def health():
        from local_agent.execution import descriptor
        return {**manager.diagnostics(), "pause_supported": False,
                'restore_pending': manager.restore_pending.is_set(),
                "dependencies": {name: importlib.util.find_spec(name) is not None
                                 for name in ("playwright", "pywinauto", "pyautogui", "PIL")},
                "workspace": config["paths"]["workspace"], "default_model": config["model"]["name"],
                "inference_defaults": asdict(InferenceOptions.from_config(config["model"])),
                "permissions": {"origins": config["browser"]["allowed_origins"],
                                "applications": list(config["desktop"]["applications"]),
                                "commands": list(config["commands"]),
                                "coding_execution": descriptor(config)}}

    @app.post('/backups')
    def backup(body: BackupBody):
        return create_backup(manager, confirmed=body.confirmed)

    @app.get('/retention')
    def retention_settings():
        return retention.settings()

    @app.post('/retention/policy')
    def retention_policy(body: RetentionPolicyBody):
        return retention.save(body.model_dump())

    @app.post('/retention/preview')
    def retention_preview(body: RetentionPreviewBody):
        return retention.preview(body.protected)

    @app.post('/retention/apply')
    def retention_apply(body: RetentionApplyBody):
        return retention.apply(body.preview, confirmed=body.confirmed)

    @app.get('/backups')
    def backups_list():
        return backup_inventory(manager)

    @app.get('/backups/{ident}')
    def backup_inspection(ident: str):
        return inspect_backup(manager, ident)

    @app.get('/restore/status')
    def restore_status():
        return read_pointer(config) or {'generation': None, 'rollback': None, 'rollback_sha256': None}

    @app.post('/restore/prepare')
    def restore_preparation(body: RestorePreparationBody):
        return prepare_restore(manager, body.backup, body.sha256, confirmed=body.confirmed)

    @app.post('/restore/activate')
    def restore_activation(body: RestoreActivationBody):
        if body.confirmed is not True:
            raise Denied('Confirm restoring Studio data and restarting the backend')
        with manager.lock:
            if manager.running:
                raise ValueError('Finish all owned tasks before restoring')
        with restore_gate.freeze():
            return activate_restore(manager, owner, body.preparation, body.sha256,
                                    confirmed=body.confirmed, require_restart=restore_gate.require_restart)

    @app.get("/conversations")
    def conversations():
        return manager.store.conversations()

    @app.get("/history/conversations")
    def conversation_history(limit: int = Query(default=50, ge=1, le=100),
                             cursor: str | None = Query(default=None, max_length=2048),
                             query: str = Query(default="", max_length=120)):
        return history_page(manager.store, "conversations", limit=limit, cursor=cursor, query=query)

    @app.get("/history/conversations/{ident}/messages")
    def message_history(ident: str, limit: int = Query(default=50, ge=1, le=100),
                        cursor: str | None = Query(default=None, max_length=2048)):
        return history_page(manager.store, "messages", conversation=ident, limit=limit, cursor=cursor)

    @app.get("/history/conversations/{ident}")
    def conversation_metadata(ident: str):
        return manager.store.conversation_metadata(ident)

    @app.get("/history/conversations/{ident}/export")
    def export_conversation(ident: str):
        return export_markdown(manager.store, ident)

    @app.get("/history/tasks")
    def task_history(limit: int = Query(default=50, ge=1, le=100),
                     cursor: str | None = Query(default=None, max_length=2048),
                     conversation: str = Query(default="", max_length=128)):
        return history_page(manager.store, "tasks", conversation=conversation, limit=limit, cursor=cursor)

    @app.get("/history/tasks/{task}")
    def task_metadata(task: str):
        return manager.task_metadata(task)

    @app.get("/preferences")
    def preferences():
        return manager.store.preferences()

    @app.post("/preferences")
    def save_preferences(body: PreferencesBody):
        return manager.store.preferences(body.model_dump())

    @app.post("/conversations")
    def create_conversation(body: ConversationBody):
        return {"id": manager.store.conversation(body.title)}

    @app.get("/conversations/{ident}/messages")
    def messages(ident: str):
        return manager.store.messages(ident)

    @app.get("/commands")
    def commands():
        return [asdict(command) for command in COMMANDS]

    @app.get("/memory")
    def memory_search(project: str = Query(default=".", max_length=1000),
                      query: str = Query(default="", max_length=500)):
        with manager.lock:
            sources = manager.memory_sources.cached(project) if manager.running else UNSET
        return manager.memory.search(project, query, listing=not query.strip(), sources=sources)

    @app.get('/memory/sources')
    def memory_sources(project: str = Query(default='.', max_length=1000)):
        return manager.memory_sources.list(project)

    @app.post('/memory/sources/preview')
    def memory_source_preview(body: MemorySourcePreviewBody):
        return manager.memory_sources.preview(body.project, body.path)

    @app.post('/memory/sources')
    def memory_source_import(body: MemorySourceBody):
        return manager.memory_sources.import_file(body.project, body.conversation, body.path, body.sha256,
            body.version, body.expected_generation, confirmed=body.confirmed)

    @app.post('/memory/sources/check')
    def memory_source_check(body: MemorySourceCheckBody):
        manager.memory_sources.prepare(body.project)
        return manager.memory_sources.list(body.project)

    @app.post('/memory/sources/{ident}/forget')
    def memory_source_forget(ident: str, body: MemorySourceForgetBody):
        manager.memory_sources.forget(body.project, ident, confirmed=body.confirmed)
        return {'forgotten': True}

    @app.get('/memory/index')
    def memory_index_status(project: str = Query(default='.', max_length=1000)):
        return manager.memory_index.status(project)

    @app.post('/memory/index')
    def memory_index_create(body: MemoryIndexBody):
        return manager.memory_index.reindex(body.project, body.model, confirmed=body.confirmed, forbidden=(token,))

    @app.get('/memory/hybrid')
    def memory_hybrid_search(project: str = Query(default='.', max_length=1000),
                             query: str = Query(min_length=1, max_length=500)):
        return manager.memory_index.search(project, query, forbidden=(token,))

    @app.post('/memory/index/enabled')
    def memory_index_enabled(body: MemoryEnabledBody):
        return manager.memory_index.set_enabled(body.project, body.enabled, confirmed=body.confirmed)

    @app.get("/memory/{ident}")
    def memory_source(ident: str, project: str = Query(default=".", max_length=1000)):
        with manager.lock:
            sources = manager.memory_sources.cached(project) if manager.running else UNSET
        return manager.memory.search(project, ident=ident, sources=sources)

    @app.post("/memory")
    def remember(body: MemoryBody):
        return manager.memory.remember(body.project, body.conversation, body.text, body.message, forbidden=(token,))

    @app.post("/memory/{ident}/forget")
    def forget(ident: str, body: ForgetBody):
        manager.memory.forget(body.project, ident, confirmed=body.confirmed)
        return {"forgotten": True}

    @app.get("/conversations/{ident}/goal")
    def current_goal(ident: str):
        manager.store.conversation_metadata(ident)
        return {"goal": manager.store.current_goal(ident)}

    @app.post("/conversations/{ident}/rename")
    def rename_conversation(ident: str, body: ConversationBody):
        manager.store.rename_conversation(ident, body.title)
        return {"renamed": True}

    @app.post("/conversations/{ident}/delete")
    def delete_conversation(ident: str, body: ConfirmationBody):
        if not body.confirmed:
            raise ValueError("Confirm conversation deletion first")
        with manager.lock:
            if any(state["conversation"] == ident for state in manager.running.values()):
                raise ValueError("Finish or cancel this conversation's active task before deleting it")
            manager.memory.before_delete(ident)
            removed = manager.store.delete_conversation(ident)
            manager.discard_events(removed)
        return {"deleted": True}

    @app.get("/conversations/{ident}/attachments")
    def pending_attachments(ident: str):
        manager.store.conversation_metadata(ident)
        return manager.store.attachments(ident, pending=True)

    @app.post("/conversations/{ident}/attachments")
    async def upload_attachment(ident: str, request: Request, name: str):
        manager.store.conversation_metadata(ident)
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > MAX_UPLOAD:
                raise HTTPException(413, "Attachment exceeds 5 MiB")
            data.extend(chunk)
        return manager.store.attachment(ident, parse_attachment(name, bytes(data)))

    @app.post("/conversations/{ident}/screenshot")
    def capture_screenshot(ident: str, body: ConfirmationBody):
        if not body.confirmed:
            raise ValueError("Screen capture requires explicit confirmation")
        manager.store.conversation_metadata(ident)
        from PIL import ImageGrab
        image = ImageGrab.grab(all_screens=False)
        image.thumbnail((1600, 1600))
        output = io.BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=88)
        return manager.store.attachment(ident, parse_attachment("screenshot.jpg", output.getvalue()))

    @app.get("/conversations/{ident}/attachments/{attachment}")
    def read_attachment(ident: str, attachment: str):
        rows = manager.store.attachments(ident, ids=[attachment], include_data=True)
        row = rows[0]
        return {"id": row["id"], "name": row["name"], "mime": row["mime"], "size": row["size"],
                "text": row["text"], "image": base64.b64encode(row["data"]).decode() if row["data"] else None}

    @app.post("/conversations/{ident}/attachments/{attachment}/remove")
    def remove_attachment(ident: str, attachment: str):
        manager.store.delete_attachment(ident, attachment)
        return {"removed": True}

    @app.get("/tasks")
    def tasks():
        return {"tasks": manager.tasks(), "approvals": manager.pending()}

    @app.get("/activity")
    def current_activity():
        with manager.lock:
            return {"tasks": manager.activity_tasks(), "approvals": manager.pending()}

    @app.get("/tasks/{task}/verifications")
    def verifications(task: str):
        return manager.store.verifications(task)

    @app.get("/tasks/{task}/diagnostics")
    def task_diagnostics(task: str):
        return manager.store.diagnostics(task, forbidden=(token,))

    @app.get("/tasks/{task}/journal")
    def task_journal(task: str):
        return manager.store.journal(task)

    @app.get("/tasks/{task}/journal/{operation}/inspect")
    def inspect_journal(task: str, operation: str):
        return inspect_operation(manager.store, config, task, operation)

    def launch_task(body: TaskBody, goal_id=None):
        # Source changes can invalidate image-bearing history before vision admission.
        sources = manager.memory_sources.prepare(body.project) if body.mode in MEMORY_MODES else None
        options = {key: getattr(body, key) for key in InferenceOptions.__dataclass_fields__}
        model = Ollama({**config["model"], **options, "name": body.model})
        history = manager.store.messages(body.conversation, for_model=True)
        selected = manager.store.attachments(body.conversation, ids=body.attachments)
        images = any(item["mime"].startswith("image/") for item in selected + [
            attachment for message in history for attachment in message["attachments"]])
        if body.mode not in {"test", "diff"}:
            model.admit(tools=body.mode in {"agent", "browser", "desktop", "coding"}, vision=images)
        return {"id": manager.start(body.conversation, body.objective, body.mode, body.model,
                                    body.project, options,
                                    body.regenerate, body.attachments, goal_id, profile=body.profile,
                                    _source_preflight=sources)}

    @app.post("/tasks")
    def start(body: TaskBody):
        return launch_task(body)

    @app.post('/inspections')
    def inspection_start(body: InspectionBody):
        if token in body.objective or any(token in path for path in body.files):
            raise Denied('Session credentials cannot be inspection inputs')
        options = {key: getattr(body, key) for key in InferenceOptions.__dataclass_fields__}
        try:
            return {'id': start_inspection(manager, body.conversation, body.objective, body.model,
                                          body.project, body.files, options)}
        except Stopped:
            raise HTTPException(409, 'Inspection interrupted by emergency stop') from None

    @app.get('/schedules')
    def schedules():
        return scheduler.summary()

    @app.post('/schedules')
    def schedule_create(body: ScheduleBody):
        if any(token in value for value in [body.objective, body.model, body.project, *body.files]):
            raise Denied('Session credentials cannot be schedule inputs')
        options = {key: getattr(body, key) for key in InferenceOptions.__dataclass_fields__}
        return {'id': scheduler.create(body.conversation, body.objective, body.model, body.project,
            body.files, options, body.interval_ms, body.misfire, body.timezone)}

    @app.post('/schedules/{ident}/enabled')
    def schedule_enable(ident: str, body: ScheduleEnabledBody):
        return scheduler.enabled(ident, body.enabled)

    @app.post('/scheduler/pause')
    def scheduler_pause(body: SchedulerPauseBody):
        if not body.paused and not body.confirmed:
            raise Denied('Confirm resuming automatic read-only inspections')
        return scheduler.set_paused(body.paused)

    @app.get('/watches')
    def directory_watches():
        return scheduler.watches.summary()

    @app.post('/watches')
    def directory_watch_create(body: DirectoryWatchBody):
        if any(token in value for value in [body.objective, body.model, body.project, body.directory, *body.files]):
            raise Denied('Session credentials cannot be watch inputs')
        options = {key: getattr(body, key) for key in InferenceOptions.__dataclass_fields__}
        return {'id': scheduler.watches.create(body.conversation, body.objective, body.model, body.project,
            body.files, options, body.directory, body.debounce_ms)}

    @app.post('/watches/{ident}/enabled')
    def directory_watch_enable(ident: str, body: ScheduleEnabledBody):
        return scheduler.watches.enabled(ident, body.enabled)

    @app.get('/tasks/{task}/inspection')
    def inspection_status(task: str):
        return inspection_summary(manager, task)

    @app.post('/tasks/{task}/inspection/pause')
    def inspection_pause(task: str, body: EmptyBody):
        return pause_inspection(manager, task)

    @app.post('/tasks/{task}/inspection/resume')
    def inspection_resume(task: str, body: EmptyBody):
        try:
            return {'id': resume_inspection(manager, task)}
        except Stopped:
            raise HTTPException(409, 'Inspection resume refused while emergency stop is latched') from None

    @app.post("/slash")
    def slash(body: TaskBody):
        if body.regenerate:
            raise ValueError("Slash commands cannot be regenerated; use the original task response")
        command, argument = parse_command(body.objective)
        if command.name in {"remember", "recall"}:
            if body.attachments:
                raise ValueError("Memory commands accept explicit text only; send attachments separately")
            manager.store.conversation_metadata(body.conversation)
            if not argument:
                raise ValueError(f"Usage: /{command.name} <text>")
            if command.name == "remember":
                records = [manager.memory.remember(body.project, body.conversation, argument, forbidden=(token,))]
            else:
                records = manager.memory.search(body.project, argument)
            return {"action": "memory", "records": records, "notice":
                    "\n\n".join(f"memory:{record['id']} (source chat {record['conversation']})\n{record['text']}"
                                for record in records) or "No matching project memories."}

        def execute(objective, mode, project=None, goal_id=None):
            task_body = body.model_copy(update={"objective": objective, "mode": mode, "project": project or body.project})
            task = launch_task(task_body, goal_id)
            return {"action": "task", "id": task["id"], "mode": mode}

        return dispatch_command(manager, body, execute)

    @app.post("/tasks/{task}/cancel")
    def cancel(task: str):
        manager.cancel(task)
        return {"cancelled": True}

    @app.post("/emergency-stop")
    def emergency():
        manager.close()
        return {"stopped": True}

    @app.post("/tasks/{task}/approvals/{ident}")
    def approval(task: str, ident: str, body: ApprovalBody):
        manager.approve(task, ident, body.approved)
        return {"answered": True}

    @app.post("/project")
    def project(body: ProjectBody):
        root = Path(config["paths"]["workspace"]).resolve()
        path = Path(body.path)
        if path.is_absolute():
            path = path.resolve()
            if not path.is_relative_to(root):
                raise Denied("Choose a directory inside the configured workspace")
            relative = str(path.relative_to(root))
        else:
            relative = body.path
        selected = Policy(config).path(relative)
        if not selected.is_dir():
            raise ValueError("Project directory does not exist")
        return {"project": relative}

    @app.get("/files")
    def files(project: str = "."):
        return Coding(Policy(config)).files(project)

    @app.get("/file")
    def read_file(path: str):
        return clean(Coding(Policy(config)).read(path))

    @app.get("/search")
    def search_files(query: str = Query(min_length=1, max_length=256), project: str = ".",
                     limit: int = Query(default=50, ge=1, le=100)):
        try:
            return clean(Coding(Policy(config)).search(query, project, limit))
        except Stopped:
            raise HTTPException(409, "Search interrupted by the stop latch") from None

    @app.get("/models")
    def models():
        model_config = dict(config["model"], timeout=3)
        try:
            model = Ollama(model_config)
            return {"running": True, "models": model.request("/api/tags").get("models", []),
                    "loaded": model.request("/api/ps").get("models", []),
                    "diagnostics": owned_model.snapshot()}
        except (OSError, ValueError) as exc:
            return {"running": False, "models": [], "loaded": [], "error": redact(str(exc)),
                    "diagnostics": owned_model.snapshot()}

    @app.get("/models/capabilities")
    def capabilities(model: str = Query(min_length=1, max_length=200)):
        # Metadata only: this endpoint never generates text, loads or unloads a model.
        selected = Ollama({**config["model"], "name": model, "thinking": None, "timeout": 5})
        return selected.admit()

    @app.post("/models/start")
    def start_ollama():
        with model_lock:
            return start_owned_ollama()

    def start_owned_ollama():
        if models()["running"]:
            return {"started": False, "message": "Using existing Ollama service"}
        if owned_model.proc and owned_model.proc.poll() is None:
            return {"started": False, "message": "Ollama is still starting"}
        argv, env = ollama_launch(config)
        owned_model.start(argv, env)
        return {"started": True, "message": "Starting local Ollama; model status will refresh"}

    @app.get("/telemetry")
    def telemetry():
        result = {"cpu_percent": None, "memory_used": None, "memory_total": None, "gpu": None}
        try:
            import psutil
            memory = psutil.virtual_memory()
            result.update(cpu_percent=psutil.cpu_percent(), memory_used=memory.used, memory_total=memory.total)
        except ImportError:
            pass
        executable = shutil.which("nvidia-smi")
        if executable:
            try:
                completed = subprocess.run([executable, "--query-gpu=utilization.gpu,memory.used,memory.total",
                                            "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                           timeout=3, check=True,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                values = [int(x.strip()) for x in completed.stdout.splitlines()[0].split(",")]
                result["gpu"] = dict(zip(("percent", "used_mib", "total_mib"), values))
            except (OSError, ValueError, IndexError, subprocess.SubprocessError):
                pass
        return result

    @app.websocket("/events")
    async def events(socket: WebSocket):
        # WebSockets do not use the HTTP Request dependency.
        if socket.headers.get("origin") not in ORIGINS:
            await socket.close(code=1008)
            return
        await socket.accept()
        try:
            try:
                auth = await asyncio.wait_for(socket.receive_json(), timeout=5)
            except (TimeoutError, ValueError, KeyError, TypeError):
                # Invalid JSON, binary frames and silent peers must get a close frame,
                # not an abandoned accepted connection or an unhandled ASGI exception.
                await socket.close(code=1008)
                return
            if (not isinstance(auth, dict) or not isinstance(auth.get("token"), str)
                    or not auth["token"].isascii() or not secrets.compare_digest(auth["token"], token)):
                await socket.close(code=1008)
                return
            after = auth.get("after", 0)
            if type(after) is not int or not 0 <= after <= 2**63 - 1:
                # SQLite event cursors are nonnegative signed 64-bit integers.
                await socket.close(code=1008)
                return
            store_id = auth.get("store_id")
            if store_id is not None and (not isinstance(store_id, str) or len(store_id) != 32
                                         or any(c not in "0123456789abcdef" for c in store_id)):
                await socket.close(code=1008)
                return
            await EventStream(socket, manager, after, store_id).run()
        except (WebSocketDisconnect, TimeoutError, ValueError, RuntimeError):
            return

    return app
