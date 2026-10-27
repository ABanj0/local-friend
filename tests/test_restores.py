"""Restore rehearsal is real SQLite recovery into fresh state, never activation."""
import hashlib
import json
import multiprocessing
import os
import sqlite3
from contextlib import closing
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from local_agent.safety import Denied
from local_agent.studio import backups, restores
from local_agent.studio.manager import Manager
from local_agent.studio.migrations import REQUIRED
from local_agent.studio.store import Store

from . import studio_support as fixtures
from .inspection_support import seed_closed_checkpoint
from .support import WorkspaceTest


def crash_prepare(config, item, phase):
    manager = Manager(config)

    def crash(*args, **kwargs):
        os._exit(23)

    owner, attribute = (backups, 'create') if phase == 'before_rollback' else (restores.json, 'dumps')
    with patch.object(owner, attribute, crash):
        restores.prepare(manager, item['id'], item['sha256'], confirmed=True)


class RestoreTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.manager = Manager(self.config)
        self.addCleanup(self.manager.close)
        self.store = self.manager.store
        self.chat = self.store.conversation('Saved private recovery')
        attachment = self.store.attachment(self.chat, {'name': 'private.bin', 'mime': 'application/octet-stream',
            'data': b'\x00\xffPRIVATE-RECOVERY', 'text': None})
        self.store.message(self.chat, 'user', 'Restored café', attachment_ids=[attachment['id']])
        self.store.preferences({'model': 'fixture', 'context': 8192})
        self.goal = self.store.create_goal(self.chat, 'Stored goal')
        self.store.set_goal_plan(self.goal['id'], ['Review recovery'])
        self.manager.memory.remember('.', self.chat, text='Saved project note')
        task = self.store.task(self.chat, 'agent', 'fixture', goal=self.goal['id'])
        with self.store.connection() as db:
            db.execute("INSERT INTO execution_steps VALUES ('step',?,1,'completed','observed',1,2)", (task,))
            db.execute("INSERT INTO operations VALUES ('op',?,'step',1,'read_file','read',?,'[]',"
                       "'completed','observed','[]',1,2)", (task, 'a' * 64))
        self.store.verification(task, {'id': 'b' * 32, 'kind': 'artifact', 'version': 1,
            'path': 'example.txt', 'expected_bytes': 0, 'expected_sha256': hashlib.sha256(b'').hexdigest(),
            'observed_bytes': 0, 'observed_sha256': hashlib.sha256(b'').hexdigest(),
            'resource_version': 'c' * 64, 'observation': 'read', 'status': 'passed', 'reason': 'content_matches'})
        self.store.finish(task, 'reported', {'report': 'Retained result'})
        seed_closed_checkpoint(self.config, self.store, self.chat)
        self.item = backups.create(self.manager, confirmed=True)
        self.source = self.policy.state / 'backups' / self.item['filename']
        self.root = self.policy.state / 'restore-staging'

    def prepare(self, **kwargs):
        return restores.prepare(self.manager, self.item['id'], self.item['sha256'], confirmed=True, **kwargs)

    def changed_source(self, statement=None, *, raw=None):
        if raw is None:
            with closing(sqlite3.connect(self.source)) as db, db:
                db.execute(statement)
        else:
            self.source.write_bytes(raw)
        self.item['sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def test_prepared_state_preserves_records_renews_identity_and_rolls_back_current_data(self):
        current = self.store.conversation('Newer current conversation')
        source_bytes = self.source.read_bytes()
        with closing(sqlite3.connect(self.source)) as db:
            before = {table: db.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall() for table in REQUIRED}
        self.assertTrue(all(before.values()), 'Preservation must exercise every required table with actual rows')
        prepared = self.prepare()
        target = self.root / prepared['id'] / 'studio.sqlite3'
        self.assertFalse(prepared['activated'])
        self.assertEqual(prepared['backup_sha256'], self.item['sha256'])
        self.assertEqual(prepared['database_sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertEqual(prepared['bytes'], target.stat().st_size)
        self.assertNotEqual(prepared['store_id'], self.store.identity)
        self.assertEqual(self.source.read_bytes(), source_bytes)
        self.assertEqual({p.name for p in target.parent.iterdir()}, {'studio.sqlite3', 'ready.json'})
        self.assertEqual(json.loads((target.parent / 'ready.json').read_text()), prepared)
        with closing(sqlite3.connect(target)) as db:
            self.assertEqual(restores.validate_schema(db), prepared['store_id'])
            for table, rows in before.items():
                if table != 'metadata':
                    self.assertEqual(db.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall(), rows, table)
        restored = Store(target)  # Independent fresh-state startup; no active state is switched.
        self.assertEqual([row['id'] for row in restored.conversations()], [self.chat])
        self.assertEqual(restored.messages(self.chat)[0]['content'], 'Restored café')
        self.assertEqual(restored.attachments(self.chat, message=restored.messages(self.chat)[0]['id'],
            include_data=True)[0]['data'], b'\x00\xffPRIVATE-RECOVERY')
        self.assertEqual(restored.current_goal(self.chat)['id'], self.goal['id'])
        self.assertEqual(self.store.path, self.policy.state / 'studio.sqlite3')
        self.assertEqual({row['id'] for row in self.store.conversations()}, {current, self.chat})
        rollback = self.policy.state / 'backups' / (prepared['rollback'] + '.sqlite3')
        self.assertEqual(hashlib.sha256(rollback.read_bytes()).hexdigest(), prepared['rollback_sha256'])
        with closing(sqlite3.connect(rollback)) as db:
            self.assertEqual({row[0] for row in db.execute('SELECT id FROM conversations')}, {self.chat, current})
        self.assertNotIn('private', json.dumps(prepared).lower())
        self.assertNotIn(str(self.policy.state), json.dumps(prepared))

    def test_confirmation_ids_hashes_and_owned_states_fail_before_staging(self):
        for confirmed in (False, None, 1, 'true'):
            with self.assertRaises(Denied):
                restores.prepare(self.manager, self.item['id'], self.item['sha256'], confirmed=confirmed)
        for ident, digest in [('../outside', self.item['sha256']), (self.item['id'], 'bad'),
                              ('C:\\secret', self.item['sha256']), (False, self.item['sha256'])]:
            with self.assertRaises(ValueError):
                restores.prepare(self.manager, ident, digest, confirmed=True)
        with self.assertRaises(Denied):
            restores.prepare(self.manager, self.item['id'], 'f' * 64, confirmed=True)
        with self.assertRaises(KeyError):
            restores.prepare(self.manager, 'e' * 32, self.item['sha256'], confirmed=True)
        for state in ({'done': False}, {'done': True}, {'done': True, 'persist_error': 'private'}):
            self.manager.running['owner'] = state
            try:
                with self.assertRaises(ValueError):
                    self.prepare()
            finally:
                self.manager.running.clear()
        self.manager.shutdown_requested.set()
        with self.assertRaises(ValueError):
            self.prepare()
        self.manager.shutdown_requested.clear()
        (self.policy.state / 'STOP').touch()
        with self.assertRaises(Denied):
            self.prepare()
        self.assertFalse(self.root.exists())

    def test_corrupt_future_missing_schema_and_invalid_references_never_become_ready(self):
        original = self.source.read_bytes()
        changes = [None, 'PRAGMA user_version=99', 'DELETE FROM schema_migrations WHERE version=4',
                   'DROP TABLE preferences',
                   "INSERT INTO messages(id,conversation,role,content,created) VALUES ('orphan','absent','user','x',1)"]
        for change in changes:
            self.source.write_bytes(original)
            self.changed_source(change, raw=b'Not a database' if change is None else None)
            with self.assertRaises((ValueError, sqlite3.DatabaseError)):
                self.prepare()
            self.assertEqual(list(self.root.iterdir()), [])
            self.assertEqual(len(list((self.policy.state / 'backups').iterdir())), 1)
            self.assertEqual(self.store.conversations()[0]['title'], 'Saved private recovery')

    def test_hostile_triggers_views_indexes_and_changed_defaults_are_not_installed(self):
        original = self.source.read_bytes()
        changes = ["CREATE TRIGGER bad AFTER UPDATE ON metadata BEGIN DELETE FROM conversations; END",
                   'CREATE VIEW extra AS SELECT content FROM messages',
                   'CREATE INDEX extra_index ON messages(content)']
        for change in changes:
            self.source.write_bytes(original)
            self.changed_source(change)
            with self.assertRaisesRegex(ValueError, 'unsupported schema'):
                self.prepare()
            self.assertEqual(list(self.root.iterdir()), [])
        # Normalization cannot erase data inside SQL literals to accept a changed default.
        self.assertNotEqual(restores._normalize("DEFAULT 'unified'"), restores._normalize("DEFAULT 'uni fied'"))
        self.assertNotEqual(restores._normalize("DEFAULT 'unified'"), restores._normalize("DEFAULT 'uni\"fied'"))

    def test_legacy_current_version_schema_is_accepted_without_rewriting_source(self):
        from .test_migrations import MigrationTests

        # Reuse the explicit independent v0 fixture builder, never inherit its test cases.
        old = Store(MigrationTests.legacy(self))
        with closing(sqlite3.connect(old.path)) as db:
            self.assertEqual(restores.validate_schema(db), old.identity)

    def test_source_hardlink_and_journal_companion_are_refused(self):
        alias = self.policy.state / 'alias.sqlite3'
        os.link(self.source, alias)
        with self.assertRaises(Denied):
            self.prepare()
        alias.unlink()
        companion = self.source.with_name(self.source.name + '-wal')
        companion.write_bytes(b'UNKNOWN-COMPANION')
        with self.assertRaises(Denied):
            self.prepare()
        self.assertEqual(companion.read_bytes(), b'UNKNOWN-COMPANION')
        self.assertFalse(self.root.exists())

    def test_bounds_rollback_failure_and_ready_marker_failure_preserve_current_data(self):
        for context, error in [(patch.object(backups, 'MAX_BYTES', 4096), Denied),
                               (patch.object(restores, 'TIMEOUT', -1), TimeoutError),
                               (patch.object(backups, 'create', side_effect=OSError('Snapshot failed')), OSError)]:
            with context, self.assertRaises(error):
                self.prepare()
            self.assertFalse(self.root.exists() and list(self.root.iterdir()))
        original_open = type(self.source).open

        def failed_marker(path, *args, **kwargs):
            if path.name == 'ready.json':
                raise OSError('Marker failed')
            return original_open(path, *args, **kwargs)

        with patch.object(type(self.source), 'open', failed_marker), self.assertRaises(OSError):
            self.prepare()
        self.assertEqual(list(self.root.iterdir()), [])
        # A rollback saved before marker failure is retained, rather than silently deleted.
        self.assertEqual(len(list((self.policy.state / 'backups').iterdir())), 2)
        self.assertEqual(self.store.conversations()[0]['title'], 'Saved private recovery')

    def test_preexisting_directory_capacity_and_unknown_cleanup_entries_are_preserved(self):
        self.root.mkdir()
        winner = self.root / ('a' * 32)
        winner.mkdir()
        canary = winner / 'canary'
        canary.write_bytes(b'EXISTING-DIRECTORY')
        with patch.object(restores.uuid, 'uuid4', return_value=SimpleNamespace(hex='a' * 32)), self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(canary.read_bytes(), b'EXISTING-DIRECTORY')
        for i in range(4):
            (self.root / f'unknown-{i}').touch()
        with self.assertRaisesRegex(ValueError, 'full'):
            self.prepare()
        self.assertEqual(len(list(self.root.iterdir())), 5)

    def test_source_change_during_preparation_never_gets_ready_marker(self):
        original_validate = restores.validate_schema
        changed = False

        def mutate(db):
            nonlocal changed
            value = original_validate(db)
            if not changed:
                changed = True
                with closing(sqlite3.connect(self.source)) as writer, writer:
                    writer.execute("UPDATE conversations SET title='Concurrent change'")
            return value

        with patch.object(restores, 'validate_schema', mutate), self.assertRaises(Denied):
            self.prepare()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_copy_rejects_a_different_open_file_before_reading_or_parsing_it(self):
        foreign = self.policy.state / 'foreign.sqlite3'
        foreign.write_bytes(b'FOREIGN-PRIVATE-CANARY')
        original_open = type(self.source).open
        reads = 0

        def swapped_handle(path, *args, **kwargs):
            nonlocal reads
            if path == self.source and args and args[0] == 'rb':
                reads += 1
                if reads == 2:
                    return original_open(foreign, *args, **kwargs)
            return original_open(path, *args, **kwargs)

        with (patch.object(type(self.source), 'open', swapped_handle), patch.object(
                restores, 'validate_schema', side_effect=AssertionError('Must not parse a substituted source')),
                self.assertRaisesRegex(Denied, 'identity changed')):
            self.prepare()
        self.assertEqual(reads, 2)
        self.assertEqual(foreign.read_bytes(), b'FOREIGN-PRIVATE-CANARY')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_unknown_file_during_failure_is_never_recursively_deleted(self):
        original_validate = restores.validate_schema

        def add_unknown(db):
            original_validate(db)
            directory = next(self.root.iterdir())
            (directory / 'unknown.txt').write_text('KEEP UNKNOWN')
            raise ValueError('Injected failure')

        with patch.object(restores, 'validate_schema', add_unknown), self.assertRaises(ValueError):
            self.prepare()
        directory = next(self.root.iterdir())
        self.assertEqual({p.name for p in directory.iterdir()}, {'unknown.txt'})
        self.assertEqual((directory / 'unknown.txt').read_text(), 'KEEP UNKNOWN')

    def test_actual_crash_before_rollback_or_ready_leaves_unaccepted_state_and_current_data(self):
        for phase in ('before_rollback', 'before_ready'):
            process = multiprocessing.get_context('spawn').Process(target=crash_prepare,
                args=(self.config, self.item, phase))
            process.start()
            try:
                process.join(10)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 23)
            finally:
                if process.is_alive():
                    process.terminate()
                    process.join(3)
                process.close()
        self.assertEqual(len(list(self.root.iterdir())), 2)
        for directory in self.root.iterdir():
            self.assertFalse((directory / 'ready.json').exists())
            self.assertTrue((directory / 'studio.sqlite3').is_file())
        prepared = self.prepare()
        self.assertFalse(prepared['activated'])
        self.assertEqual(len(list(self.root.iterdir())), 3)
        self.assertEqual(self.store.conversations()[0]['title'], 'Saved private recovery')


@skipUnless(fixtures.HAS_API, 'Install desktop dependencies')
class RestoreAPITests(fixtures.StudioAPIFixture, WorkspaceTest):
    def test_authenticated_strict_confirmed_preparation_keeps_current_data(self):
        manager = self.client.app.state.manager
        chat = manager.store.conversation('Saved API recovery')
        item = backups.create(manager, confirmed=True)
        body = {'backup': item['id'], 'sha256': item['sha256'], 'confirmed': True}
        self.assertEqual(self.client.post('/restore/prepare', json=body).status_code, 401)
        self.assertEqual(self.client.post('/restore/prepare', headers={**self.headers, 'Origin': 'https://bad.invalid'}, json=body).status_code, 403)
        for invalid in ({**body, 'destination': '../outside'}, {**body, 'backup': '../escape'},
                        {**body, 'confirmed': 1}, {**body, 'sha256': 'bad'}):
            self.assertEqual(self.client.post('/restore/prepare', headers=self.headers, json=invalid).status_code, 422)
        self.assertEqual(self.client.post('/restore/prepare', headers=self.headers,
            json={**body, 'confirmed': False}).status_code, 403)
        response = self.client.post('/restore/prepare', headers=self.headers, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()['activated'])
        self.assertEqual(manager.store.conversations()[0]['id'], chat)
        self.assertNotIn('Saved API recovery', response.text)
        self.assertNotIn(str(self.policy.state), response.text)


class RestoreProcessTests(fixtures.StudioProcessFixture, WorkspaceTest):
    def test_real_owned_approval_wait_denies_preparation_then_denial_allows_rehearsal(self):
        item = backups.create(self.manager, confirmed=True)
        task = self.manager.start(self.conversation, 'Create reviewed file', 'agent', 'fixture')
        self.wait_until(lambda: bool(self.manager.pending()))
        with self.assertRaises(ValueError):
            restores.prepare(self.manager, item['id'], item['sha256'], confirmed=True)
        approval = self.manager.pending()[0]
        self.manager.approve(task, approval['id'], False)
        self.wait_until(lambda: not self.manager.running)
        prepared = restores.prepare(self.manager, item['id'], item['sha256'], confirmed=True)
        self.assertFalse(prepared['activated'])
        self.assertFalse((self.policy.root / 'review.txt').exists())
