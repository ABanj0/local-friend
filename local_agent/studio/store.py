import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from local_agent.agent import clean
from local_agent.observability import MAX_SPANS, diagnostic, exclude_values, hex_id
from local_agent.studio import journal
from local_agent.studio.migrations import migrate
from local_agent.verification import validate as validate_verification


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            migrate(db)
            self.identity = db.execute("SELECT value FROM metadata WHERE key='store_id'").fetchone()[0]

    @contextmanager
    def connection(self):
        # Do not hold the supervisor's cancellation lock behind a long SQLite busy wait.
        db = sqlite3.connect(self.path, timeout=0.2)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def conversation(self, title="New conversation"):
        ident = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("INSERT INTO conversations(id,title,created) VALUES (?,?,?)", (ident, clean(title[:120]), time.time()))
        return ident

    def conversations(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM conversations ORDER BY created DESC")]

    def conversation_metadata(self, ident):
        with self.connection() as db:
            row = db.execute('SELECT id,title,created FROM conversations WHERE id=?', (ident,)).fetchone()
            if row is None:
                raise KeyError('Conversation not found')
            return dict(row)

    def rename_conversation(self, ident, title):
        if not title.strip():
            raise ValueError("Enter a conversation name")
        with self.connection() as db:
            if not db.execute("UPDATE conversations SET title=? WHERE id=?", (clean(title.strip()[:120]), ident)).rowcount:
                raise KeyError("Conversation not found")

    def delete_conversation(self, ident):
        with self.connection() as db:
            return self.delete_conversation_in(db, ident)

    @staticmethod
    def delete_conversation_in(db, ident):
        """Same cascades for single deletion and a caller-owned atomic retention batch."""
        if not db.execute("SELECT 1 FROM conversations WHERE id=?", (ident,)).fetchone():
            raise KeyError("Conversation not found")
        removed_tasks = {row["id"] for row in db.execute("SELECT id FROM tasks WHERE conversation=?", (ident,))}
        db.execute("DELETE FROM events WHERE task IN (SELECT id FROM tasks WHERE conversation=?)", (ident,))
        db.execute("DELETE FROM tasks WHERE conversation=?", (ident,))
        db.execute("DELETE FROM attachments WHERE conversation=?", (ident,))
        db.execute("DELETE FROM messages WHERE conversation=?", (ident,))
        db.execute("DELETE FROM goals WHERE conversation=?", (ident,))
        db.execute("DELETE FROM conversations WHERE id=?", (ident,))
        return removed_tasks

    def attachment(self, conversation, parsed):
        ident = uuid.uuid4().hex
        size = len(parsed["data"]) if parsed["text"] is None else len(parsed["text"].encode())
        with self.connection() as db:
            if db.execute("SELECT count(*) FROM attachments WHERE conversation=? AND message IS NULL", (conversation,)).fetchone()[0] >= 4:
                raise ValueError("At most four pending attachments per conversation")
            db.execute("INSERT INTO attachments VALUES (?,?,NULL,?,?,?,?,?)",
                       (ident, conversation, parsed["name"], parsed["mime"], parsed["data"], parsed["text"], size))
        return {"id": ident, "name": parsed["name"], "mime": parsed["mime"], "size": size}

    def attachments(self, conversation, *, message=None, ids=None, pending=False, include_data=False):
        columns = "*" if include_data else "id,name,mime,size"
        query, args = f"SELECT {columns} FROM attachments WHERE conversation=?", [conversation]
        if pending:
            query += " AND message IS NULL"
        elif message is not None:
            query += " AND message=?"
            args.append(message)
        if ids is not None:
            if len(ids) > 4 or len(set(ids)) != len(ids):
                raise ValueError("Select at most four different attachments")
            query += " AND id IN (" + (','.join('?' for _ in ids) or 'NULL') + ")"
            args.extend(ids)
        with self.connection() as db:
            rows = [dict(row) for row in db.execute(query, args)]
        if ids is not None:
            found = {row["id"]: row for row in rows}
            if any(ident not in found for ident in ids):
                raise ValueError("Attachment does not belong to this conversation")
            rows = [found[ident] for ident in ids]
        return rows if include_data else [{key: row[key] for key in ("id", "name", "mime", "size")} for row in rows]

    def delete_attachment(self, conversation, ident):
        with self.connection() as db:
            if not db.execute("DELETE FROM attachments WHERE conversation=? AND id=? AND message IS NULL",
                              (conversation, ident)).rowcount:
                raise ValueError("Only pending attachments can be removed")

    def preferences(self, value=None):
        with self.connection() as db:
            if value is not None:
                db.execute("INSERT INTO preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                           (json.dumps(value),))
            row = db.execute("SELECT payload FROM preferences WHERE id=1").fetchone()
            return json.loads(row["payload"]) if row else {}

    def messages(self, conversation, *, for_model=False):
        with self.connection() as db:
            if not db.execute("SELECT 1 FROM conversations WHERE id=?", (conversation,)).fetchone():
                raise KeyError("Conversation not found")
            rows = [{**dict(row), "metrics": json.loads(row["metrics"]) if row["metrics"] else None}
                    for row in db.execute(
                        "SELECT * FROM messages WHERE conversation=? "
                        + ("AND memory_epoch=(SELECT memory_epoch FROM conversations WHERE id=?) " if for_model else "")
                        + "ORDER BY created,rowid", (conversation, conversation) if for_model else (conversation,))]
        return [{**row, "attachments": self.attachments(conversation, message=row["id"])} for row in rows]

    def message(self, conversation, role, content, metrics=None, attachment_ids=None):
        ident = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("INSERT INTO messages(id,conversation,role,content,created,metrics,memory_epoch) "
                       "VALUES (?,?,?,?,?,?,(SELECT memory_epoch FROM conversations WHERE id=?))",
                       (ident, conversation, role, clean(content), time.time(),
                        json.dumps(metrics) if metrics is not None else None, conversation))
            for attachment in attachment_ids or []:
                if not db.execute("UPDATE attachments SET message=? WHERE id=? AND conversation=? AND message IS NULL",
                                  (ident, attachment, conversation)).rowcount:
                    raise ValueError("Attachment was already sent or is not available")
        return ident

    def task(self, conversation, mode, model, goal=None, profile="unified", *, project=None, scope_key=None, memory_refs=None,
             inspection=None, resume_from=None, queue_claim=None):
        ident = uuid.uuid4().hex
        if queue_claim is not None and (inspection is None or resume_from is not None):
            raise ValueError('Queue admission requires a fresh read-only inspection')
        with self.connection() as db:
            if inspection is not None:
                from local_agent.studio.inspection import encode, load, require, validate_spec
                db.execute('BEGIN IMMEDIATE')
                require(mode == 'inspection' and goal is None and profile == 'coding')
                validate_spec(inspection['spec'])
                spec = inspection['spec']
                require(spec['model'] == model and spec['project'] == project and spec['scope'] == scope_key
                        and not memory_refs)
                epoch = db.execute('SELECT memory_epoch FROM conversations WHERE id=?', (conversation,)).fetchone()
                require(epoch is not None and epoch[0] == inspection['spec']['epoch'])
                if resume_from:
                    previous = load(db, resume_from[0])
                    source = db.execute('SELECT conversation,status FROM tasks WHERE id=?', (resume_from[0],)).fetchone()
                    require(source['conversation'] == conversation and source['status'] in {'failed', 'interrupted'}
                            and previous['state'] in {'ready', 'paused'} and previous['resumed_by'] is None
                            and previous['sha256'] == resume_from[1])
                    require(previous['data']['agent'] is not None)
                    expected = {**previous['data']['spec'], 'attempt': previous['data']['spec']['attempt'] + 1,
                                'prior_reads': len(previous['data']['agent']['evidence'])}
                    require(inspection == {'spec': expected, 'agent': previous['data']['agent']})
                else:
                    require(inspection['agent'] is None and spec['attempt'] == 1 and spec['prior_reads'] == 0)
                if queue_claim is not None:
                    from local_agent.studio.work_queue import validate_admission
                    validate_admission(db, queue_claim, spec, conversation)
            db.execute("INSERT INTO tasks(id,conversation,mode,status,model,created,result,goal,profile,journal_version,project,scope_key,memory_refs) "
                       "VALUES (?,?,?,?,?,?,NULL,?,?,1,?,?,?)",
                       (ident, conversation, mode, "running", model, time.time(), goal, profile, project, scope_key,
                        json.dumps(memory_refs or [])))
            if inspection is not None:
                import hashlib
                payload = encode(inspection)
                db.execute("INSERT INTO inspection_checkpoints VALUES (?,?,?,?,?,NULL,?)",
                           (ident, 'ready' if inspection['agent'] is not None else 'initial',
                            payload, hashlib.sha256(payload.encode()).hexdigest(),
                            resume_from[0] if resume_from else None, time.time()))
                if resume_from:
                    db.execute("UPDATE inspection_checkpoints SET state='consumed',resumed_by=?,updated=? WHERE task=?",
                               (ident, time.time(), resume_from[0]))
                if queue_claim is not None:
                    from local_agent.studio.work_queue import attach
                    attach(db, queue_claim, ident)
        return ident

    def latest_task(self, conversation):
        with self.connection() as db:
            row = db.execute("SELECT * FROM tasks WHERE conversation=? ORDER BY created DESC,rowid DESC LIMIT 1",
                             (conversation,)).fetchone()
            return dict(row) if row else None

    def current_goal(self, conversation):
        with self.connection() as db:
            row = db.execute("SELECT * FROM goals WHERE conversation=? ORDER BY created DESC,rowid DESC LIMIT 1",
                             (conversation,)).fetchone()
            return {**dict(row), "steps": json.loads(row["steps"])} if row else None

    def create_goal(self, conversation, objective):
        if not objective.strip() or len(objective) > 12000:
            raise ValueError("Goal objective must contain 1–12,000 characters")
        with self.connection() as db:
            if db.execute("SELECT 1 FROM goals WHERE conversation=? AND status='active'", (conversation,)).fetchone():
                raise ValueError("A goal is already active; complete or cancel it before creating another")
            now = time.time()
            db.execute("INSERT INTO goals(id,conversation,objective,status,steps,created,updated) VALUES (?,?,?,'active','[]',?,?)",
                       (uuid.uuid4().hex, conversation, clean(objective.strip()), now, now))
        return self.current_goal(conversation)

    def set_goal_plan(self, ident, steps):
        if not steps or len(steps) > 30 or not all(isinstance(step, str) and 0 < len(step) <= 2000 for step in steps):
            raise ValueError("Goal checklist must contain 1–30 nonempty steps")
        with self.connection() as db:
            db.execute("UPDATE goals SET steps=?,updated=?,memory_epoch=(SELECT memory_epoch FROM conversations "
                       "WHERE id=goals.conversation) WHERE id=? AND status='active' AND steps='[]'",
                       (json.dumps([{"text": clean(step), "done": False} for step in steps]), time.time(), ident))

    def goal_step(self, conversation, index, done):
        with self.connection() as db:
            row = db.execute("SELECT * FROM goals WHERE conversation=? AND status='active'", (conversation,)).fetchone()
            if not row:
                raise ValueError("No active goal")
            steps = json.loads(row["steps"])
            if not 0 <= index < len(steps):
                raise ValueError("Invalid goal step number")
            steps[index]["done"] = done
            db.execute("UPDATE goals SET steps=?,updated=? WHERE id=?", (json.dumps(steps), time.time(), row["id"]))

    def finish_goal(self, conversation, status):
        if status not in {"completed", "cancelled"}:
            raise ValueError("Invalid goal status")
        with self.connection() as db:
            row = db.execute("SELECT * FROM goals WHERE conversation=? AND status='active'", (conversation,)).fetchone()
            if not row:
                raise ValueError("No active goal")
            steps = json.loads(row["steps"])
            if status == "completed" and (not steps or not all(step["done"] for step in steps)):
                raise ValueError("Review and mark every checklist step done before completing the goal")
            db.execute("UPDATE goals SET status=?,updated=? WHERE id=?", (status, time.time(), row["id"]))

    def finish(self, task, status, result):
        with self.connection() as db:
            db.execute("UPDATE tasks SET status=?,result=? WHERE id=?",
                       (status, json.dumps(clean(result)), task))

    def complete(self, task, result):
        """Commit one terminal outcome, assistant message and result event, or none of them."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            return self._complete(db, task, result)

    def _complete(self, db, task, result):
        result = clean(result)
        status = result["status"]
        if status not in {"reported", "planned", "no_actions", "blocked", "failed", "cancelled", "interrupted"}:
            raise ValueError("Invalid terminal task status")
        row = db.execute("SELECT conversation,status,goal,memory_refs FROM tasks WHERE id=?", (task,)).fetchone()
        if row is None:
            raise KeyError("Task not found")
        if row["status"] not in {"running", "waiting"}:
            return None  # First terminal outcome wins, including across connections/restarts.
        if status == "planned" and row["goal"]:
            steps = result["plan"]["steps"]
            if not steps or len(steps) > 30 or not all(isinstance(s, str) and 0 < len(s) <= 2000 for s in steps):
                raise ValueError("Invalid goal plan")
            db.execute("UPDATE goals SET steps=?,updated=?,memory_epoch=(SELECT memory_epoch FROM conversations "
                       "WHERE id=goals.conversation) WHERE id=? AND status='active' AND steps='[]'",
                       (json.dumps([{"text": s, "done": False} for s in steps]), time.time(), row["goal"]))
        now = time.time()
        refs = json.loads(row["memory_refs"])
        result.pop("memory_sources", None)  # A worker cannot invent server-owned retrieval provenance.
        if refs:
            result["memory_sources"] = refs
            result["report"] = result.get("report", result.get("reason", "Task ended")) + (
                "\n\nRetrieved memory (historical notes; not independent verification): "
                + ", ".join("memory:" + ref for ref in refs))
        journal.reconcile(db, task)
        if status not in {'failed', 'interrupted'}:
            db.execute("UPDATE inspection_checkpoints SET state='closed' WHERE task=? AND state<>'consumed'", (task,))
        db.execute("UPDATE tasks SET status=?,result=? WHERE id=?", (status, json.dumps(result), task))
        db.execute("INSERT INTO messages(id,conversation,role,content,created,metrics,memory_epoch) "
                   "VALUES (?,?,?,?,?,?,(SELECT memory_epoch FROM conversations WHERE id=?))",
                   (uuid.uuid4().hex, row["conversation"], "assistant",
                    result.get("report", result.get("reason", "Task ended")), now,
                    json.dumps(result["metrics"]) if result.get("metrics") is not None else None, row["conversation"]))
        cursor = db.execute("INSERT INTO events(task,kind,payload,created) VALUES (?,?,?,?)",
                            (task, "result", json.dumps(result), now))
        return {"seq": cursor.lastrowid, "task": task, "kind": "result", "payload": result}

    def waiting(self, task, waiting):
        with self.connection() as db:
            db.execute("UPDATE tasks SET status=? WHERE id=? AND status IN ('running','waiting')",
                       ("waiting" if waiting else "running", task))

    def inspection_checkpoint(self, task, payload, *, paused=False):
        from local_agent.studio.inspection import save
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            summary = save(db, task, payload, paused=paused)
            return self._journal_event(db, task, 'inspection_checkpoint', summary)

    @staticmethod
    def _journal_active(db, task):
        row = db.execute("SELECT status,journal_version FROM tasks WHERE id=?", (task,)).fetchone()
        if row is None:
            raise KeyError("Task not found")
        if row["journal_version"] != 1:
            raise ValueError("Task has no supported journal")
        return row["status"] in {"running", "waiting"}

    @staticmethod
    def _journal_event(db, task, kind, payload):
        cursor = db.execute("INSERT INTO events(task,kind,payload,created) VALUES (?,?,?,?)",
                            (task, kind, json.dumps(payload), time.time()))
        return {"seq": cursor.lastrowid, "task": task, "kind": kind, "payload": payload}

    def record_step(self, task, payload):
        payload = journal.step(payload, task)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if not self._journal_active(db, task):
                return None
            now = time.time()
            if payload["phase"] == "started":
                db.execute("INSERT INTO execution_steps VALUES (?,?,?,'running',NULL,?,?)",
                           (payload["id"], task, payload["index"], now, now))
            else:
                row = db.execute("SELECT ordinal,state FROM execution_steps WHERE id=? AND task=?", (payload["id"], task)).fetchone()
                if row is None or row["ordinal"] != payload["index"] or row["state"] != "running":
                    raise ValueError("Invalid journal step completion")
                pending = list(db.execute("SELECT effect FROM operations WHERE step=? AND state='intent'", (payload["id"],)))
                state = "unknown" if any(r["effect"] != "read" for r in pending) else "interrupted" if pending or payload["status"] in {"cancelled", "interrupted"} else "completed"
                db.execute("UPDATE execution_steps SET state=?,outcome=?,updated=? WHERE id=?",
                           (state, payload["status"], now, payload["id"]))
            return self._journal_event(db, task, "trace", payload)

    def operation_intent(self, task, payload):
        payload = journal.intent(payload)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if not self._journal_active(db, task):
                return None
            parent = db.execute("SELECT state FROM execution_steps WHERE id=? AND task=?", (payload["step"], task)).fetchone()
            if parent is None or parent["state"] != "running":
                raise ValueError("Operation needs an active decision")
            if db.execute("SELECT 1 FROM operations WHERE id=?", (payload["id"],)).fetchone():
                raise ValueError("Duplicate operation cannot authorize another dispatch")
            ordinal = db.execute("SELECT count(*) FROM operations WHERE task=?", (task,)).fetchone()[0] + 1
            if ordinal > journal.MAX_OPERATIONS or db.execute("SELECT 1 FROM operations WHERE task=? AND state='intent'", (task,)).fetchone():
                raise ValueError("Operation budget or ordering violation")
            now = time.time()
            db.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?,?,'intent',NULL,'[]',?,?)",
                       (payload["id"], task, payload["step"], ordinal, payload["tool"], payload["effect"],
                        payload["arguments_sha256"], json.dumps(payload["preconditions"]), now, now))
            return self._journal_event(db, task, "operation_intent", payload)

    def operation_result(self, task, payload):
        payload = journal.result(payload)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if not self._journal_active(db, task):
                return None
            row = db.execute("SELECT task,state,outcome,verification_ids FROM operations WHERE id=?", (payload["id"],)).fetchone()
            if row is None or row["task"] != task:
                raise ValueError("Unknown operation result")
            if row["state"] == "completed" and row["outcome"] == payload["outcome"] and json.loads(row["verification_ids"]) == payload["verification_ids"]:
                return None
            if row["state"] != "intent":
                raise ValueError("Operation result cannot replace an earlier outcome")
            for ident in payload["verification_ids"]:
                if not db.execute("SELECT 1 FROM verifications WHERE id=? AND task=?", (ident, task)).fetchone():
                    raise ValueError("Operation references unknown evidence")
            db.execute("UPDATE operations SET state='completed',outcome=?,verification_ids=?,updated=? WHERE id=?",
                       (payload["outcome"], json.dumps(payload["verification_ids"]), time.time(), payload["id"]))
            return self._journal_event(db, task, "operation_result", payload)

    def journal(self, task):
        if not hex_id(task):
            raise KeyError("Task not found")
        with self.connection() as db:
            db.execute("BEGIN")
            row = db.execute("SELECT status,journal_version FROM tasks WHERE id=?", (task,)).fetchone()
            if row is None:
                raise KeyError("Task not found")
            steps = [dict(r) for r in db.execute("SELECT id,ordinal,state,outcome,created,updated FROM execution_steps WHERE task=? ORDER BY ordinal LIMIT ?", (task, journal.MAX_STEPS + 1))]
            operations = [dict(r) for r in db.execute("SELECT id,step,ordinal,tool,effect,arguments_sha256,"
                "CASE WHEN length(CAST(preconditions AS BLOB))<=8192 THEN preconditions END AS preconditions,"
                "state,outcome,CASE WHEN length(verification_ids)<=512 THEN verification_ids END AS verification_ids,created,updated "
                "FROM operations WHERE task=? ORDER BY ordinal LIMIT ?", (task, journal.MAX_OPERATIONS + 1))]
        partial = len(steps) > journal.MAX_STEPS or len(operations) > journal.MAX_OPERATIONS
        safe_steps, safe_operations = [], []
        for item in steps[:journal.MAX_STEPS]:
            if (hex_id(item["id"]) and type(item["ordinal"]) is int and 1 <= item["ordinal"] <= journal.MAX_STEPS
                    and item["state"] in {"running", "completed", "interrupted", "unknown"}
                    and (item["outcome"] is None or item["outcome"] in journal.STATUSES)
                    and journal.timestamp(item["created"]) and journal.timestamp(item["updated"])):
                safe_steps.append(item)
            else:
                partial = True
        for item in operations[:journal.MAX_OPERATIONS]:
            try:
                item["preconditions"] = json.loads(item["preconditions"])
                item["verification_ids"] = json.loads(item["verification_ids"])
                journal.intent({"version": 1, **{k: item[k] for k in ("id", "step", "tool", "effect", "arguments_sha256", "preconditions")}})
                journal.result({"version": 1, "id": item["id"], "outcome": item["outcome"] or "inconclusive", "verification_ids": item["verification_ids"]})
                journal.require(item["state"] in {"intent", "completed", "interrupted", "unknown"})
                journal.require(type(item["ordinal"]) is int and 1 <= item["ordinal"] <= journal.MAX_OPERATIONS
                                and journal.timestamp(item["created"]) and journal.timestamp(item["updated"]))
                journal.require((item["state"] == "completed" and item["outcome"] in journal.OUTCOMES)
                                or (item["state"] != "completed" and item["outcome"] is None and item["verification_ids"] == []))
                safe_operations.append(item)
            except (ValueError, TypeError, RecursionError):
                partial = True
        return {"version": 1, "task": task, "task_state": row["status"], "available": row["journal_version"] == 1,
                "partial": partial, "steps": safe_steps, "operations": safe_operations, "replay_supported": False}

    def tasks(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM tasks ORDER BY created DESC LIMIT 200")]

    def verification(self, task, payload):
        payload = validate_verification(payload)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM tasks WHERE id=?", (task,)).fetchone()
            if row is None:
                raise KeyError("Task not found")
            if row["status"] not in {"running", "waiting"}:
                return None
            existing = db.execute("SELECT task,payload FROM verifications WHERE id=?", (payload["id"],)).fetchone()
            if existing:
                if existing["task"] != task or json.loads(existing["payload"]) != payload:
                    raise ValueError("Verification identity conflict")
                return None
            now = time.time()
            db.execute("INSERT INTO verifications VALUES (?,?,?,?)", (payload["id"], task, json.dumps(payload), now))
            cursor = db.execute("INSERT INTO events(task,kind,payload,created) VALUES (?,?,?,?)",
                                (task, "verification", json.dumps(payload), now))
            return {"seq": cursor.lastrowid, "task": task, "kind": "verification", "payload": payload}

    def verifications(self, task):
        with self.connection() as db:
            return [{"task": task, "created": row["created"], **json.loads(row["payload"])} for row in reversed(
                list(db.execute("SELECT payload,created FROM verifications WHERE task=? ORDER BY created DESC,rowid DESC LIMIT 200",
                                (task,))))]

    def event(self, task, kind, payload):
        # Never persist image bytes or approval bodies that can contain sensitive input.
        persisted = {"transient": True} if kind in {"preview", "approval"} else clean(payload)
        with self.connection() as db:
            cursor = db.execute("INSERT INTO events(task,kind,payload,created) VALUES (?,?,?,?)",
                                (task, kind, json.dumps(persisted), time.time()))
            return {"seq": cursor.lastrowid, "task": task, "kind": kind, "payload": clean(payload)}

    def events(self, after=0):
        with self.connection() as db:
            return [{**dict(row), "payload": json.loads(row["payload"])} for row in db.execute(
                "SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT 1000", (after,))]

    def diagnostics(self, task, *, forbidden=()):
        if not hex_id(task):
            raise KeyError("Task not found")
        with self.connection() as db:
            db.execute("BEGIN")  # One consistent read snapshot; no execution or state reconciliation.
            row = db.execute("SELECT id,status,CASE WHEN length(CAST(result AS BLOB))<=1048576 THEN result END AS result "
                             "FROM tasks WHERE id=?", (task,)).fetchone()
            if row is None:
                raise KeyError("Task not found")
            traces = list(db.execute("SELECT CASE WHEN length(CAST(payload AS BLOB))<=4096 THEN payload END AS payload "
                                     "FROM events WHERE task=? AND kind='trace' ORDER BY seq LIMIT ?", (task, MAX_SPANS * 2 + 1)))
            checks = list(db.execute("SELECT CASE WHEN length(CAST(payload AS BLOB))<=4096 THEN payload END AS payload "
                                     "FROM verifications WHERE task=? ORDER BY created,rowid LIMIT 201", (task,)))

        def parsed(value):
            try:
                return json.loads(value) if value else None
            except (ValueError, TypeError, RecursionError):
                return None

        result = {**dict(row), "result": parsed(row["result"])}
        exported = diagnostic(result, [parsed(item["payload"]) for item in traces[:MAX_SPANS * 2]],
                              [parsed(item["payload"]) for item in checks[:200]],
                              truncated=len(traces) > MAX_SPANS * 2 or len(checks) > 200)
        return exclude_values(exported, forbidden)

    def event_high_water(self):
        with self.connection() as db:
            # Allocated sequence, not MAX surviving row: deleting a chat must not rewind cursors.
            row = db.execute("SELECT seq FROM sqlite_sequence WHERE name='events'").fetchone()
            return row[0] if row else 0

    def event_page(self, after, through):
        from local_agent.studio.event_stream import MAX_FRAME_BYTES, PAGE_BYTES, PAGE_SIZE
        result, size = [], 0
        with self.connection() as db:
            for row in db.execute("SELECT * FROM events WHERE seq>? AND seq<=? ORDER BY seq LIMIT ?",
                                  (after, through, PAGE_SIZE)):
                event = {**dict(row), "payload": json.loads(row["payload"])}
                length = len(json.dumps(event, ensure_ascii=False).encode("utf-8"))
                if length > MAX_FRAME_BYTES - 16384:
                    raise OverflowError("Activity item exceeds the delivery size limit")
                if result and size + length > PAGE_BYTES:
                    break
                result.append(event)
                size += length
        return result

    def recover(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            tasks = list(db.execute("SELECT id FROM tasks WHERE status IN ('running','waiting')"))
            for row in tasks:
                self._complete(db, row["id"], {"status": "interrupted", "report":
                    "Backend restarted before task completion. No actions were replayed."})
