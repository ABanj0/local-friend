"""Numbered SQLite schema changes. Never replay application actions or repair data."""
import time
import uuid

BASE = (
    "CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY,title TEXT NOT NULL,created REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY,payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),role TEXT NOT NULL,content TEXT NOT NULL,created REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),mode TEXT NOT NULL,status TEXT NOT NULL,model TEXT NOT NULL,created REAL NOT NULL,result TEXT)",
    "CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT,task TEXT NOT NULL REFERENCES tasks(id),kind TEXT NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL)",
    "CREATE INDEX IF NOT EXISTS events_task_kind_seq ON events(task,kind,seq)",
    "CREATE TABLE IF NOT EXISTS verifications (id TEXT PRIMARY KEY,task TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,payload TEXT NOT NULL,created REAL NOT NULL)",
    "CREATE TABLE IF NOT EXISTS attachments (id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),message TEXT REFERENCES messages(id),name TEXT NOT NULL,mime TEXT NOT NULL,data BLOB NOT NULL,text TEXT,size INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS goals (id TEXT PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id),objective TEXT NOT NULL,status TEXT NOT NULL,steps TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL)",
)


def columns(db, table):
    # Only trusted table constants reach this helper.
    return {row[1] for row in db.execute(f"PRAGMA table_info({table})")}


def add_column(db, table, name, declaration):
    if name not in columns(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")


def legacy_store(db):
    for statement in BASE:
        db.execute(statement)  # executescript would commit a pending legacy transaction.
    add_column(db, "messages", "metrics", "TEXT")
    add_column(db, "tasks", "goal", "TEXT REFERENCES goals(id)")
    add_column(db, "tasks", "profile", "TEXT NOT NULL DEFAULT 'unified'")
    db.execute("INSERT OR IGNORE INTO metadata VALUES ('store_id',?)", (uuid.uuid4().hex,))


def operation_journal(db):
    add_column(db, "tasks", "journal_version", "INTEGER NOT NULL DEFAULT 0")
    add_column(db, "tasks", "project", "TEXT")
    add_column(db, "tasks", "scope_key", "TEXT")
    db.execute("""CREATE TABLE execution_steps (
        id TEXT PRIMARY KEY,task TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        ordinal INTEGER NOT NULL,state TEXT NOT NULL,outcome TEXT,created REAL NOT NULL,
        updated REAL NOT NULL,UNIQUE(task,ordinal))""")
    db.execute("""CREATE TABLE operations (
        id TEXT PRIMARY KEY,task TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        step TEXT NOT NULL REFERENCES execution_steps(id) ON DELETE CASCADE,
        ordinal INTEGER NOT NULL,tool TEXT NOT NULL,effect TEXT NOT NULL,
        arguments_sha256 TEXT NOT NULL,preconditions TEXT NOT NULL,state TEXT NOT NULL,
        outcome TEXT,verification_ids TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,
        UNIQUE(task,ordinal))""")
    db.execute("CREATE INDEX operations_task_step ON operations(task,step,ordinal)")


def project_memory(db):
    add_column(db, "conversations", "memory_scope", "TEXT")
    add_column(db, "conversations", "memory_epoch", "INTEGER NOT NULL DEFAULT 0")
    add_column(db, "messages", "memory_epoch", "INTEGER NOT NULL DEFAULT 0")
    add_column(db, "goals", "memory_epoch", "INTEGER NOT NULL DEFAULT 0")
    add_column(db, "tasks", "memory_refs", "TEXT NOT NULL DEFAULT '[]'")
    db.execute("CREATE TABLE memory_domains(scope TEXT PRIMARY KEY,epoch INTEGER NOT NULL DEFAULT 0)")
    db.execute("""CREATE TABLE memories(
        id TEXT PRIMARY KEY,scope TEXT NOT NULL REFERENCES memory_domains(scope),
        conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        message TEXT REFERENCES messages(id) ON DELETE CASCADE,
        text TEXT NOT NULL,sha256 TEXT NOT NULL,created REAL NOT NULL)""")
    db.execute("CREATE INDEX memories_scope ON memories(scope,created)")
    db.execute("""CREATE TRIGGER memory_forgotten AFTER DELETE ON memories BEGIN
        UPDATE memory_domains SET epoch=epoch+1 WHERE scope=OLD.scope;
        UPDATE conversations SET memory_epoch=(SELECT epoch FROM memory_domains WHERE scope=OLD.scope)
          WHERE memory_scope=OLD.scope;
        END""")


def history_paging(db):
    # SQLite index entries include rowid; reverse scans preserve same-timestamp order.
    db.execute("CREATE INDEX conversations_history ON conversations(created)")
    db.execute("CREATE INDEX messages_history ON messages(conversation,created)")
    db.execute("CREATE INDEX tasks_history ON tasks(created)")
    db.execute("CREATE INDEX tasks_conversation_history ON tasks(conversation,created)")
    db.execute("CREATE INDEX attachments_message_history ON attachments(conversation,message)")


def inspection_checkpoints(db):
    db.execute("""CREATE TABLE inspection_checkpoints(
        task TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
        state TEXT NOT NULL,payload TEXT NOT NULL,sha256 TEXT NOT NULL,
        source_task TEXT REFERENCES tasks(id) ON DELETE CASCADE,
        resumed_by TEXT REFERENCES tasks(id) ON DELETE SET NULL,updated REAL NOT NULL)""")


def workflow_queue(db):
    db.execute("""CREATE TABLE workflow_queue(
        id TEXT PRIMARY KEY,request_key TEXT NOT NULL UNIQUE,
        conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        payload TEXT NOT NULL,sha256 TEXT NOT NULL,state TEXT NOT NULL,owner TEXT,token_sha256 TEXT,
        expires_ms INTEGER,task TEXT UNIQUE REFERENCES tasks(id) ON DELETE SET NULL,
        created_ms INTEGER NOT NULL,updated_ms INTEGER NOT NULL)""")
    db.execute('CREATE INDEX workflow_queue_pending ON workflow_queue(state,expires_ms,created_ms)')


def interval_schedules(db):
    db.execute('CREATE TABLE interval_schedules(id TEXT PRIMARY KEY,conversation TEXT NOT NULL '
               'REFERENCES conversations(id) ON DELETE CASCADE,payload TEXT NOT NULL,sha256 TEXT NOT NULL,'
               'enabled INTEGER NOT NULL,interval_ms INTEGER NOT NULL,next_ms INTEGER NOT NULL,'
               'misfire TEXT NOT NULL,timezone TEXT NOT NULL,status TEXT NOT NULL,created_ms INTEGER NOT NULL)')
    db.execute('CREATE TABLE schedule_runs(job TEXT PRIMARY KEY REFERENCES workflow_queue(id) ON DELETE CASCADE,'
               'schedule TEXT NOT NULL REFERENCES interval_schedules(id) ON DELETE CASCADE,due_ms INTEGER NOT NULL,'
               'UNIQUE(schedule,due_ms))')
    db.execute('CREATE INDEX interval_schedules_due ON interval_schedules(enabled,next_ms)')
    db.execute('CREATE INDEX schedule_runs_recent ON schedule_runs(schedule,due_ms)')


def directory_watches(db):
    db.execute('CREATE TABLE directory_watches(id TEXT PRIMARY KEY,conversation TEXT NOT NULL '
               'REFERENCES conversations(id) ON DELETE CASCADE,payload TEXT NOT NULL,sha256 TEXT NOT NULL,'
               'directory TEXT NOT NULL,directory_scope TEXT NOT NULL,enabled INTEGER NOT NULL,'
               'debounce_ms INTEGER NOT NULL,baseline TEXT,candidate TEXT,candidate_ms INTEGER,'
               'next_ms INTEGER NOT NULL,generation INTEGER NOT NULL,revision INTEGER NOT NULL,'
               'status TEXT NOT NULL,created_ms INTEGER NOT NULL)')
    db.execute('CREATE TABLE directory_runs(job TEXT PRIMARY KEY REFERENCES workflow_queue(id) ON DELETE CASCADE,'
               'watch TEXT NOT NULL REFERENCES directory_watches(id) ON DELETE CASCADE,'
               'generation INTEGER NOT NULL,fingerprint TEXT NOT NULL,UNIQUE(watch,generation))')
    db.execute('CREATE INDEX directory_watches_due ON directory_watches(enabled,next_ms)')
    db.execute('CREATE INDEX directory_runs_recent ON directory_runs(watch,generation)')


def memory_vectors(db):
    db.execute("CREATE UNIQUE INDEX memories_scope_id ON memories(scope,id)")
    db.execute("""CREATE TABLE memory_indexes(
        scope TEXT PRIMARY KEY REFERENCES memory_domains(scope),
        identity TEXT NOT NULL,manifest TEXT NOT NULL,epoch INTEGER NOT NULL,
        generation TEXT NOT NULL,created REAL NOT NULL)""")
    db.execute("""CREATE TABLE memory_vectors(
        scope TEXT NOT NULL REFERENCES memory_indexes(scope) ON DELETE CASCADE,
        memory TEXT NOT NULL,source_sha256 TEXT NOT NULL,vector BLOB NOT NULL,vector_sha256 TEXT NOT NULL,
        PRIMARY KEY(scope,memory),
        FOREIGN KEY(scope,memory) REFERENCES memories(scope,id) ON DELETE CASCADE)""")


def memory_file_sources(db):
    db.execute("""CREATE TABLE memory_file_sources(
        id TEXT PRIMARY KEY,scope TEXT NOT NULL REFERENCES memory_domains(scope),
        conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        path TEXT NOT NULL,sha256 TEXT NOT NULL,version TEXT NOT NULL,view TEXT NOT NULL,
        generation TEXT NOT NULL,state TEXT NOT NULL,reason TEXT NOT NULL,created REAL NOT NULL,
        UNIQUE(scope,path),UNIQUE(scope,id))""")
    db.execute("""CREATE TABLE memory_file_chunks(
        scope TEXT NOT NULL,memory TEXT NOT NULL,source TEXT NOT NULL,ordinal INTEGER NOT NULL,
        start_char INTEGER NOT NULL,end_char INTEGER NOT NULL,start_line INTEGER NOT NULL,end_line INTEGER NOT NULL,
        PRIMARY KEY(memory),UNIQUE(source,ordinal),
        FOREIGN KEY(scope,memory) REFERENCES memories(scope,id) ON DELETE CASCADE,
        FOREIGN KEY(scope,source) REFERENCES memory_file_sources(scope,id) ON DELETE CASCADE)""")
    db.execute("""CREATE TRIGGER memory_file_removed BEFORE DELETE ON memory_file_sources BEGIN
        DELETE FROM memories WHERE scope=OLD.scope AND id IN
          (SELECT memory FROM memory_file_chunks WHERE source=OLD.id AND scope=OLD.scope);
        END""")
    db.execute("""CREATE TRIGGER memory_file_stale AFTER UPDATE OF state ON memory_file_sources
        WHEN OLD.state='current' AND NEW.state='stale' BEGIN
        DELETE FROM memory_vectors WHERE scope=NEW.scope AND memory IN
          (SELECT memory FROM memory_file_chunks WHERE source=NEW.id AND scope=NEW.scope);
        UPDATE memory_domains SET epoch=epoch+1 WHERE scope=NEW.scope;
        UPDATE conversations SET memory_epoch=(SELECT epoch FROM memory_domains WHERE scope=NEW.scope)
          WHERE memory_scope=NEW.scope;
        END""")


MIGRATIONS = (("legacy_store", legacy_store), ("operation_journal", operation_journal),
              ("project_memory", project_memory), ("history_paging", history_paging),
              ("inspection_checkpoints", inspection_checkpoints), ("workflow_queue", workflow_queue),
              ("interval_schedules", interval_schedules), ("directory_watches", directory_watches),
              ("memory_vectors", memory_vectors), ("memory_file_sources", memory_file_sources))
SCHEMA_VERSION = len(MIGRATIONS)
REQUIRED = {
    "conversations": {"id", "title", "created", "memory_scope", "memory_epoch"}, "preferences": {"id", "payload"},
    "metadata": {"key", "value"}, "messages": {"id", "conversation", "role", "content", "created", "metrics"},
    "tasks": {"id", "conversation", "mode", "status", "model", "created", "result", "goal", "profile", "journal_version", "project", "scope_key"},
    "events": {"seq", "task", "kind", "payload", "created"}, "verifications": {"id", "task", "payload", "created"},
    "attachments": {"id", "conversation", "message", "name", "mime", "data", "text", "size"},
    "goals": {"id", "conversation", "objective", "status", "steps", "created", "updated"},
    "execution_steps": {"id", "task", "ordinal", "state", "outcome", "created", "updated"},
    "operations": {"id", "task", "step", "ordinal", "tool", "effect", "arguments_sha256", "preconditions", "state", "outcome", "verification_ids", "created", "updated"},
    "memory_domains": {"scope", "epoch"},
    "memories": {"id", "scope", "conversation", "message", "text", "sha256", "created"},
    "inspection_checkpoints": {"task", "state", "payload", "sha256", "source_task", "resumed_by", "updated"},
    "workflow_queue": {"id", "request_key", "conversation", "payload", "sha256", "state", "owner",
                       "token_sha256", "expires_ms", "task", "created_ms", "updated_ms"},
    'interval_schedules': {'id', 'conversation', 'payload', 'sha256', 'enabled', 'interval_ms',
                           'next_ms', 'misfire', 'timezone', 'status', 'created_ms'},
    'schedule_runs': {'job', 'schedule', 'due_ms'},
    'directory_watches': {'id', 'conversation', 'payload', 'sha256', 'directory', 'directory_scope', 'enabled',
                          'debounce_ms', 'baseline', 'candidate', 'candidate_ms', 'next_ms', 'generation',
                          'revision', 'status', 'created_ms'},
    'directory_runs': {'job', 'watch', 'generation', 'fingerprint'},
    'memory_indexes': {'scope', 'identity', 'manifest', 'epoch', 'generation', 'created'},
    'memory_vectors': {'scope', 'memory', 'source_sha256', 'vector', 'vector_sha256'},
    'memory_file_sources': {'id', 'scope', 'conversation', 'path', 'sha256', 'version', 'view',
                            'generation', 'state', 'reason', 'created'},
    'memory_file_chunks': {'scope', 'memory', 'source', 'ordinal', 'start_char', 'end_char', 'start_line', 'end_line'},
}
REQUIRED["messages"].add("memory_epoch")
REQUIRED["tasks"].add("memory_refs")
REQUIRED["goals"].add("memory_epoch")


def migrate(db):
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if not 0 <= version <= SCHEMA_VERSION:
        raise ValueError("Unsupported Studio database version; use a compatible application")
    db.execute("BEGIN IMMEDIATE")
    try:
        # Re-read under the writer lock in case another initializer just migrated.
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if not 0 <= version <= SCHEMA_VERSION:
            raise ValueError("Unsupported Studio database version")
        exists = db.execute("SELECT 1 FROM sqlite_schema WHERE name='schema_migrations'").fetchone()
        if version == 0 and exists or version and not exists:
            raise ValueError("Studio migration history is inconsistent")
        if exists:
            actual = [(row[0], row[1]) for row in db.execute("SELECT version,name FROM schema_migrations ORDER BY version")]
            expected = [(i + 1, name) for i, (name, _) in enumerate(MIGRATIONS[:version])]
            if actual != expected:
                raise ValueError("Studio migration history is inconsistent")
        else:
            db.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied REAL NOT NULL)")
        for index in range(version, SCHEMA_VERSION):
            name, apply = MIGRATIONS[index]
            apply(db)
            db.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (index + 1, name, time.time()))
        for table, expected in REQUIRED.items():
            if not expected <= columns(db, table):
                raise ValueError("Studio schema is incomplete; no automatic data repair was performed")
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    db.execute("PRAGMA journal_mode=WAL")
