"""Real SQLite migration/rollback/retention checks, never against the user's state."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from local_agent.studio import migrations
from local_agent.studio.store import Store

from .support import WorkspaceTest


class MigrationTests(WorkspaceTest):
    def test_v5_queue_migration_rolls_back_and_preserves_checkpoint_history_and_identity(self):
        from .inspection_support import spec_for
        path = self.policy.state / 'v5.db'
        required = {key: value for key, value in migrations.REQUIRED.items()
                    if key not in {'workflow_queue', 'interval_schedules', 'schedule_runs', 'directory_watches', 'directory_runs', 'memory_indexes', 'memory_vectors', 'memory_file_sources', 'memory_file_chunks'}}
        with patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:5]), \
                patch.object(migrations, 'SCHEMA_VERSION', 5), patch.object(migrations, 'REQUIRED', required):
            old = Store(path)
            chat = old.conversation('Retained v5')
            old.message(chat, 'user', 'Keep checkpoint history')
            (self.policy.root / 'a.py').write_text('# Previous inspection', encoding='utf-8')
            spec = spec_for(self.config, old, chat, files=['a.py'])
            task = old.task(chat, 'inspection', spec['model'], profile='coding', project='.', scope_key=spec['scope'],
                            inspection={'spec': spec, 'agent': None})
            old.complete(task, {'status': 'cancelled', 'report': 'Closed fixture'})
            with old.connection() as db:
                checkpoint = tuple(db.execute('SELECT * FROM inspection_checkpoints').fetchone())

        def fail(db):
            migrations.workflow_queue(db)
            raise RuntimeError('Injected queue migration failure')

        with patch.object(migrations, 'MIGRATIONS', (*migrations.MIGRATIONS[:5], ('workflow_queue', fail))), \
                self.assertRaises(RuntimeError):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 5)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_schema WHERE name='workflow_queue'").fetchone())
            self.assertEqual(db.execute('SELECT * FROM inspection_checkpoints').fetchone(), checkpoint)
        upgraded = Store(path)
        self.assertEqual(upgraded.identity, old.identity)
        self.assertEqual(upgraded.messages(chat)[0]['content'], 'Keep checkpoint history')
        with upgraded.connection() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], migrations.SCHEMA_VERSION)
            self.assertEqual(tuple(db.execute('SELECT * FROM inspection_checkpoints').fetchone()), checkpoint)
            self.assertEqual(db.execute('SELECT count(*) FROM workflow_queue').fetchone()[0], 0)

    def test_v4_upgrade_adds_checkpoints_atomically_without_rewriting_history(self):
        path = self.policy.state / 'v4.db'
        old_required = {key: value for key, value in migrations.REQUIRED.items()
                        if key not in {'inspection_checkpoints', 'workflow_queue', 'interval_schedules', 'schedule_runs', 'directory_watches', 'directory_runs', 'memory_indexes', 'memory_vectors', 'memory_file_sources', 'memory_file_chunks'}}
        with patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:4]), \
                patch.object(migrations, 'SCHEMA_VERSION', 4), patch.object(migrations, 'REQUIRED', old_required):
            old = Store(path)
            chat = old.conversation('Retained v4')
            old.message(chat, 'user', 'Keep history and identity')

        def fail(db):
            migrations.inspection_checkpoints(db)
            raise RuntimeError('Injected checkpoint migration failure')

        with patch.object(migrations, 'MIGRATIONS', (*migrations.MIGRATIONS[:4], ('inspection_checkpoints', fail))), \
                self.assertRaises(RuntimeError):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 4)
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_schema WHERE name='inspection_checkpoints'").fetchone())
            self.assertEqual(db.execute('SELECT content FROM messages').fetchone()[0], 'Keep history and identity')
        upgraded = Store(path)
        self.assertEqual(upgraded.identity, old.identity)
        self.assertEqual(upgraded.messages(chat)[0]['content'], 'Keep history and identity')
        with upgraded.connection() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], migrations.SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT count(*) FROM inspection_checkpoints').fetchone()[0], 0)

    def legacy(self):
        path = self.policy.state / "legacy.sqlite3"
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript((Path(__file__).with_name("fixtures") / "studio_v0.sql").read_text())
            db.execute("INSERT INTO conversations VALUES ('chat','Existing',1)")
            db.execute("INSERT INTO metadata VALUES ('store_id',?)", ("e" * 32,))
            db.execute("INSERT INTO preferences VALUES (1,?)", (json.dumps({"model": "fixture", "context": 8192}),))
            db.execute("INSERT INTO messages VALUES ('msg','chat','user','retained',1,?)", (json.dumps({"generated_tokens": 7}),))
            db.execute("INSERT INTO goals VALUES ('goal','chat','objective','active',?,1,2)",
                       (json.dumps([{"text": "review", "done": False}]),))
            db.execute("INSERT INTO tasks VALUES ('task','chat','agent','reported','fixture',1,?,'goal','coding')",
                       (json.dumps({"status": "reported", "report": "existing"}),))
            db.execute("INSERT INTO events VALUES (417,'task','approval',?,1)", (json.dumps({"transient": True}),))
            db.execute("INSERT INTO verifications VALUES ('check','task',?,1)", (json.dumps({"kind": "fixture"}),))
            db.execute("INSERT INTO attachments VALUES ('attachment','chat','msg','note.txt','text/plain',?,'kept',4)", (b"kept",))
        return path

    def test_legacy_data_identity_attachments_goals_and_cursor_are_preserved(self):
        path = self.legacy()
        before = {}
        with closing(sqlite3.connect(path)) as db:
            for table in ("conversations", "metadata", "preferences", "messages", "goals", "tasks", "events", "verifications", "attachments"):
                names = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
                before[table] = (names, db.execute(f"SELECT {','.join(names)} FROM {table}").fetchall())
        store = Store(path)
        self.assertEqual(store.identity, "e" * 32)
        self.assertEqual(store.event_high_water(), 417)
        with store.connection() as db:
            for table, (names, rows) in before.items():
                self.assertEqual([tuple(r) for r in db.execute(f"SELECT {','.join(names)} FROM {table}")], rows, table)
            self.assertEqual(db.execute("SELECT journal_version FROM tasks").fetchone()[0], 0)
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], migrations.SCHEMA_VERSION)
        self.assertEqual(store.event("task", "progress", {"text": "new"})["seq"], 418)
        self.assertEqual(store.messages("chat")[0]["attachments"][0]["id"], "attachment")

    def test_fresh_and_repeated_initialization_keep_identity_and_history(self):
        path = self.policy.state / "new.db"
        first = Store(path)
        with first.connection() as db:
            history = [tuple(r) for r in db.execute("SELECT * FROM schema_migrations ORDER BY version")]
        second = Store(path)
        self.assertEqual(first.identity, second.identity)
        with second.connection() as db:
            self.assertEqual([tuple(r) for r in db.execute("SELECT * FROM schema_migrations ORDER BY version")], history)
            self.assertEqual([(r[0], r[1]) for r in history],
                             [(1, "legacy_store"), (2, "operation_journal"), (3, "project_memory"),
                              (4, "history_paging"), (5, "inspection_checkpoints"), (6, "workflow_queue"),
                              (7, "interval_schedules"), (8, "directory_watches"), (9, "memory_vectors"), (10, "memory_file_sources")])
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_later_schema_failure_rolls_back_legacy_adoption_and_columns(self):
        path = self.policy.state / "partial.db"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE messages(id TEXT PRIMARY KEY,conversation TEXT,role TEXT,content TEXT,created REAL)")
            db.execute("INSERT INTO messages VALUES ('old','chat','user','kept',1)")

        def failed(db):
            db.execute("CREATE TABLE should_rollback(value TEXT)")
            raise RuntimeError("Injected migration failure")

        replacement = (migrations.MIGRATIONS[0], ("operation_journal", failed))
        with patch.object(migrations, "MIGRATIONS", replacement), self.assertRaises(RuntimeError):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("SELECT content FROM messages").fetchone()[0], "kept")
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual([r[1] for r in db.execute("PRAGMA table_info(messages)")], ["id", "conversation", "role", "content", "created"])
            self.assertEqual(db.execute("SELECT name FROM sqlite_schema WHERE type='table'").fetchall(), [("messages",)])
        self.assertEqual(len(Store(path).identity), 32)

    def test_future_or_negative_versions_fail_without_changing_data_or_journal_mode(self):
        for version in (99, -1):
            path = self.policy.state / f"future-{version}.db"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE user_data(value TEXT)")
                db.execute("INSERT INTO user_data VALUES ('retained')")
                db.execute(f"PRAGMA user_version={version}")
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "version"):
                Store(path)
            self.assertEqual(path.read_bytes(), before)

    def test_history_mismatch_or_missing_schema_is_not_silently_repaired(self):
        path = self.legacy()
        store = Store(path)
        with store.connection() as db:
            db.execute("UPDATE schema_migrations SET name='unexpected' WHERE version=1")
        with self.assertRaisesRegex(ValueError, "history"):
            Store(path)
        with store.connection() as db:
            db.execute("UPDATE schema_migrations SET name='legacy_store' WHERE version=1")
            db.execute("DROP TABLE operations")
        with self.assertRaisesRegex(ValueError, "schema"):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("SELECT content FROM messages").fetchone()[0], "retained")

    def test_version_one_applies_only_pending_journal_migration(self):
        path = self.legacy()
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied REAL NOT NULL)")
            db.execute("INSERT INTO schema_migrations VALUES (1,'legacy_store',123)")
            db.execute("PRAGMA user_version=1")
        forbidden = Mock(side_effect=AssertionError("must not rerun"))
        registry = (("legacy_store", forbidden), *migrations.MIGRATIONS[1:])
        with patch.object(migrations, "MIGRATIONS", registry):
            store = Store(path)
        forbidden.assert_not_called()
        with store.connection() as db:
            self.assertEqual(db.execute("SELECT applied FROM schema_migrations WHERE version=1").fetchone()[0], 123)
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], migrations.SCHEMA_VERSION)

    def test_concurrent_initializers_serialize_without_duplicate_migrations(self):
        path = self.policy.state / "shared.db"
        with ThreadPoolExecutor(max_workers=2) as executor:
            identities = list(executor.map(lambda _: Store(path).identity, range(2)))
        self.assertEqual(len(set(identities)), 1)
        with Store(path).connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], migrations.SCHEMA_VERSION)

    def test_version_two_upgrade_preserves_journal_and_rolls_back_failed_memory_migration(self):
        path = self.policy.state / "v2.db"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied REAL NOT NULL)")
            for index, (name, apply) in enumerate(migrations.MIGRATIONS[:2], 1):
                apply(db)
                db.execute("INSERT INTO schema_migrations VALUES (?,?,123)", (index, name))
            db.execute("PRAGMA user_version=2")
            db.execute("INSERT INTO conversations VALUES ('chat','Before memory',1)")
            db.execute("INSERT INTO messages VALUES ('message','chat','user','kept',1,NULL)")

        def fail(db):
            migrations.project_memory(db)
            raise RuntimeError("after DDL")

        with patch.object(migrations, "MIGRATIONS", (*migrations.MIGRATIONS[:2], ("project_memory", fail))), \
                self.assertRaisesRegex(RuntimeError, "after DDL"):
            Store(path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertNotIn("memory_epoch", migrations.columns(db, "messages"))
        store = Store(path)
        self.assertEqual(store.messages("chat")[0]["content"], "kept")
        with store.connection() as db:
            self.assertEqual(db.execute("SELECT applied FROM schema_migrations WHERE version=2").fetchone()[0], 123)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
